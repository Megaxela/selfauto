from asyncio import Condition, run_coroutine_threadsafe, get_event_loop

from .basic_event import BasicEvent


class Listener:
    def __init__(self, parent_component: "EventsComponent", matcher=None):
        self._parent_component: "EventsComponent" = parent_component
        self._buffer = []
        self._event_received_condition = Condition()
        self._matcher = matcher

    @property
    def parent(self) -> "EventsComponent":
        return self._parent_component

    def feed_event(self, event: BasicEvent):
        self._buffer.append(event)
        run_coroutine_threadsafe(self.__notify_event(), get_event_loop())

    async def __aenter__(self):
        self.parent.add_subscriber(self)
        return self

    async def __aexit__(self, *args, **kwargs):
        self.parent.remove_subscriber(self)

    def __aiter__(self):
        # iteration initialization code here
        return self

    async def __anext__(self) -> BasicEvent:
        while True:
            while not self._buffer:
                async with self._event_received_condition:
                    await self._event_received_condition.wait()

            event = self._buffer.pop(0)
            if self._matcher is not None:
                if self._matcher(event):
                    return event

    async def __notify_event(self):
        async with self._event_received_condition:
            self._event_received_condition.notify_all()
