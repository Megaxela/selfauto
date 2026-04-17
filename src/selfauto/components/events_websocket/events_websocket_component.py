from dataclasses import dataclass, field
from typing import Set
from json import dumps
from asyncio import create_task, wait, FIRST_COMPLETED

from aiohttp.web import Request, WebSocketResponse, WSMsgType

from selfauto.components.basic_component import BasicComponent
from selfauto.components import webserver, events

EVENTS_WS_PATH = "/api/events"


class EventsWebsocketComponent(BasicComponent):
    NAME = "events_websocket"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._events_component: events.Component | None = None

    async def on_initialize(self, _):
        self._events_component = await self.find_component(events.Component)
        webserver_component: webserver.Component = await self.find_component(
            webserver.Component
        )

        webserver_component.add_handler("GET", EVENTS_WS_PATH, self.__handle)

    async def __handle(self, request: Request):
        ws = WebSocketResponse(heartbeat=1)
        await ws.prepare(request)

        handling_tasks = [
            create_task(self.__handle_recv(ws, request)),
            create_task(self.__handle_send(ws, request)),
        ]

        _, handling_tasks = await wait(handling_tasks, return_when=FIRST_COMPLETED)

        # Cancelling pending
        for task in handling_tasks:
            task.cancel()
            await task

        return ws

    async def __handle_recv(self, ws: WebSocketResponse, request: Request):
        async for msg in ws:
            match msg.type:
                case WSMsgType.ERROR:
                    self.logger.error(
                        "Closing websocket client %s due to error: %s",
                        request.remote,
                        ws.exception(),
                    )
                    return
                case WSMsgType.CLOSE:
                    self.logger.debug(
                        "Closing websocket client %s with close code: %d",
                        request.remote,
                        ws.close_code,
                    )
                    return
                case _:  # Do nothing
                    pass

    async def __handle_send(self, ws: WebSocketResponse, request: Request):
        async with self._events_component.subscribe() as listener:
            async for event in listener:
                ws.write(dumps(event.json_dict).encode("utf-8"))
