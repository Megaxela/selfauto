from typing import ClassVar
from dataclasses import dataclass

from components.events import BasicEvent


@dataclass()
class ScheduleTriggered(BasicEvent):
    ID: ClassVar[float] = "schedule_triggered"

    label: str

    @property
    def json_data(self):
        return {"label": self.label}
