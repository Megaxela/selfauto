from asyncio import wait, Task, create_task, wait_for
from dataclasses import dataclass, field
from typing import Dict, List, Set, Iterable, Tuple
from uuid import uuid4
from logging import Logger

from selfauto.components.basic_component import BasicComponent

from selfauto.components import events
from .basic_task import BasicTask, Parameter
from .exceptions import AlreadyRunningError
from .fabric import get_task_cls, list_task_cls
from .events.task_started import TaskStarted
from .events.task_finished import TaskFinished
from .log_storage import LogStorage


@dataclass()
class TaskConfig:
    label: str
    exclusive: bool
    timeout_sec: int
    implementation: str
    config: dict


@dataclass()
class TaskClsData:
    cls: type
    exclusive: bool
    timeout_sec: int
    config: dict


@dataclass()
class RunningTask:
    task: BasicTask
    watcher_task: Task


class TasksComponent(BasicComponent):
    NAME = "tasks"

    @dataclass()
    class Config:
        tasks: List[TaskConfig] = field(default_factory=list)

    @staticmethod
    def make_default_config():
        return TasksComponent.Config(
            tasks=[
                TaskConfig(
                    label="example_label",
                    exclusive=True,
                    timeout_sec=60,
                    implementation="reboot",
                    config={},
                )
            ],
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Config | None = None

        self._task_cls: Dict[str, TaskClsData] = dict()
        self._running_tasks: Dict[str, RunningTask] = dict()
        self._running_tasks_by_task_label: Dict[str, Set[str]] = dict()
        self._events_component: events.Component | None = None
        self._log_storage: LogStorage = LogStorage()

    @property
    def task_labels(self) -> List[str]:
        return list(self._task_cls.keys())

    @property
    def running_task_ids(self) -> Iterable[Tuple[str, str]]:
        for task_id, running_task in self._running_tasks.items():
            yield (running_task.task.LABEL, task_id)

    def task_cls_data_by_label(self, label: str):
        return self._task_cls.get(label)

    async def on_initialize(self, config: Config):
        self._events_component = await self.find_component(events.Component)

        self._config = config

        for task_cfg in config.tasks:
            if task_cfg.label in self._task_cls:
                raise ValueError(
                    f"Multiple tasks with same label presented. Label: '{task_cfg.label}'"
                )

            self._task_cls[task_cfg.label] = TaskClsData(
                cls=get_task_cls(task_cfg.implementation),
                exclusive=task_cfg.exclusive,
                timeout_sec=task_cfg.timeout_sec,
                config=task_cfg.config,
            )

    async def on_deinitialize(self):
        if not self._running_tasks:
            return

        # note: this can hang indefinetely. implement some
        # kind of task cancellation.
        await wait([r.watcher_task for r in self._running_tasks])

    async def run_task(self, label: str, parameters: dict) -> BasicTask:
        cls_data = self._task_cls.get(label)
        if cls_data is None:
            raise ValueError(f"Unknown task '{label}'")

        # Generate ID
        identifier = uuid4().hex

        if cls_data.exclusive:
            if self._running_tasks_by_task_label.get(label, list()):
                raise AlreadyRunningError(
                    f"Exclusive task '{label}' is already running"
                )

        task_logger = self.service.make_logger(f"{self.NAME}.{identifier}")

        # if task_logger:
        #     task_logger.addHandler(self._log_storage.make_handler_for(identifier))

        # Creating and initializing task
        task_obj: BasicTask = cls_data.cls(
            parent_component=self,
            identifier=identifier,
            logger=task_logger,
        )
        await task_obj.initialize(cls_data.config)

        # Running task
        task_future = await task_obj.run(**parameters)
        self.try_emit_event(TaskStarted(task_id=identifier))

        running_task = RunningTask(
            task=task_obj,
            watcher_task=create_task(
                self.__watcher(
                    task_future=task_future,
                    identifier=identifier,
                    label=label,
                    timeout_sec=cls_data.timeout_sec,
                )
            ),
        )

        self._running_tasks[identifier] = running_task
        self._running_tasks_by_task_label.setdefault(label, set()).add(identifier)

        return task_obj

    async def __watcher(
        self, task_future: Task, identifier: str, label: str, timeout_sec: int | None
    ):
        self.logger.info("Watching for '%s' task", identifier)
        try:
            if timeout_sec is not None:
                await wait_for(task_future, timeout=timeout_sec)
            else:
                await task_future
        except TimeoutError:
            self.logger.info(
                "Task '%s' has been timed out. Cancelling task.", identifier
            )
            task_future.cancel("Timeout")
            await task_future
            self.logger.info("Task '%s' has cancelled.", identifier)
        except Exception as e:
            self.logger.error(
                "Task '%s' throws unhandled exception", identifier, exc_info=True
            )
        self._running_tasks.pop(identifier)
        self._running_tasks_by_task_label.get(label).remove(identifier)
        self.try_emit_event(TaskFinished(task_id=identifier))

    def try_emit_event(self, ev):
        if self._events_component is None:
            return

        self._events_component.push_event(ev)
