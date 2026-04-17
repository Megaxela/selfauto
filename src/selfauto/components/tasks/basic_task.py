from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
from typing import Dict, List
from asyncio import create_task, Task
from logging import Logger
from enum import Enum, auto

from dacite import from_dict

from selfauto.components.basic_component import BasicComponent
from .exceptions import AlreadyRunningError


class ParameterType(Enum):
    STRING = auto()
    FILE = auto()


@dataclass()
class Parameter:
    name: str
    type: ParameterType


class BasicTask(ABC):
    PARAMETERS: List[Parameter] = []

    def __init__(
        self,
        parent_component: BasicComponent,
        type_name: str,
        identifier: str,
        logger: Logger,
    ):
        self.__parent: BasicComponent = parent_component
        self.__running = False
        self.__id: str = identifier
        self.__logger: Logger = logger
        self.__type_name = type_name
        self.__task: Task | None = None

    @property
    def id(self) -> str:
        return self.__id

    @property
    def running(self) -> bool:
        return self.__running

    @property
    def parent(self) -> BasicComponent:
        return self.__parent

    @property
    def logger(self) -> Logger:
        return self.__logger

    async def initialize(self, config: Dict):
        await self.on_initialize(from_dict(type(self).Config, config))

    async def run(self, *args, **kwargs) -> Task:
        if self.__running:
            raise AlreadyRunningError("Script is already running")

        return create_task(self.__runner(*args, **kwargs), name=self.__id)

    async def __runner(self, *args, **kwargs):
        self.__running = True
        try:
            await self.on_run(*args, **kwargs)
        except Exception as e:
            self.logger.error(
                "Task '%s' received an unhandled exception: %s",
                self.__id,
                e,
                exc_info=True,
            )
        finally:
            self.__running = False

    @abstractmethod
    async def on_initialize(self, config):
        pass

    @abstractmethod
    async def on_run(self, *args, **kwargs) -> bool:
        pass
