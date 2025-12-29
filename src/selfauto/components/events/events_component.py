from dataclasses import dataclass, field
from typing import Set

from dacite import from_dict
from dataclasses import asdict

from selfauto.components.basic_component import BasicComponent

from .listener import Listener
from .basic_event import BasicEvent


class EventsComponent(BasicComponent):
    NAME = "events"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__subscribers: Set[Listener] = set()

    async def on_initialize(self, _):
        pass

    def push_event(self, event: BasicEvent):
        for sub in self.__subscribers:
            sub.feed_event(event)

    def subscribe(self, *args, **kwargs) -> Listener:
        return Listener(self, *args, **kwargs)

    def add_subscriber(self, listener: Listener):
        self.__subscribers.add(listener)

    def remove_subscriber(self, listener: Listener):
        self.__subscribers.remove(listener)

    async def run(self):
        pass
