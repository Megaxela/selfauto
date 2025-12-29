from dataclasses import dataclass
from typing import List
from datetime import datetime, timezone, timedelta
from asyncio import sleep, create_task, gather

from selfauto.components.basic_component import BasicComponent
from croniter import croniter

from components import events
from .event import ScheduleTriggered


@dataclass()
class Schedule:
    label: str
    cron_string: str


class SchedulerComponent(BasicComponent):
    NAME = "scheduler"

    @dataclass()
    class Config:
        schedules: List[Schedule]

        def __post_init__(self):
            for index, sched in enumerate(self.schedules):
                if not croniter.is_valid(sched.cron_string):
                    raise ValueError(
                        f"Schedule '{sched.label}' at index {index} has invalid cron string"
                    )

    @staticmethod
    def make_default_config() -> Config:
        return SchedulerComponent.Config(
            schedules=[
                Schedule(
                    label="sample_schedule",
                    cron_string="*/5 * * * *",
                ),
            ]
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__crons = {}
        self.__events: events.Component = None
        self.__tasks = []

    async def on_initialize(self, config: "Config"):
        self.__events = await self.find_component(events.Component)

        # Load dependencies
        for schedule in config.schedules:
            self.__crons[schedule.label] = croniter(schedule.cron_string)

    async def run(self):
        for label in self.__crons.keys():
            self.__tasks.append(create_task(self.__handle_cron(label)))
        await gather(*self.__tasks)

    async def __handle_cron(self, label: str):
        self.logger.info(f"Running cron handler for {label}")
        iterator = self.__crons.get(label)
        while True:
            now = datetime.utcnow()
            next_trigger_time = iterator.get_next(datetime)
            self.logger.info(
                f"Next '{label}' schedule will trigger at {next_trigger_time}"
            )
            if next_trigger_time > now:
                need_to_sleep_for = (next_trigger_time - now).total_seconds()
                self.logger.info(
                    f"Has to wait for '{label}' schedule for {need_to_sleep_for} seconds"
                )
                await sleep(need_to_sleep_for)

            self.__events.push_event(ScheduleTriggered(label=label))
