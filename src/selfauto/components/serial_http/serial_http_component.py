from dataclasses import dataclass, field
from typing import List, Dict
from logging import Logger
from asyncio import create_task, CancelledError, sleep

from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotModified
from aiohttp.client_exceptions import ClientConnectionResetError
from aiohttp.web import Request, WebSocketResponse, json_response, Response
from aiohttp import WSMsgType
from dacite import from_dict
from dataclasses import asdict

from selfauto.components.basic_component import BasicComponent
from selfauto.components import webserver, serial

SERIAL_PATH_TEMPLATE = "/api/serial/{label}"
SERIAL_DATA_WS_PATH_TEMPLATE = f"{SERIAL_PATH_TEMPLATE}/data"
CONNECT_PATH_TEMPLATE = f"{SERIAL_PATH_TEMPLATE}/connect"
DISCONNECT_PATH_TEMPLATE = f"{SERIAL_PATH_TEMPLATE}/disconnect"


class SerialHttpComponent(BasicComponent):
    NAME = "serial_http"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._active_connections = set()

    async def on_initialize(self, _):
        webserver_component: webserver.Component = await self.find_component(
            webserver.Component
        )

        serial_component: serial.Component = await self.find_component(serial.Component)

        for connection_label in serial_component.connection_labels:
            connection = serial_component.get_connection_by_label(connection_label)
            self.__add_handlers_for(webserver_component, connection_label, connection)

    def __add_handlers_for(
        self,
        webserver: webserver.Component,
        connection_label: str,
        connection: serial.Connection,
    ):
        template_vars = {"label": connection_label}

        # Default info handler

        webserver.add_handler(
            "GET",
            SERIAL_PATH_TEMPLATE.format(**template_vars),
            self.__make_serial_get_handler(connection),
        )

        # Connect handler
        webserver.add_handler(
            "POST",
            CONNECT_PATH_TEMPLATE.format(**template_vars),
            self.__make_serial_connect_handler(connection),
        )
        webserver.add_handler(
            "POST",
            DISCONNECT_PATH_TEMPLATE.format(**template_vars),
            self.__make_serial_disconnect_handler(connection),
        )

        webserver.add_handler(
            "GET",
            SERIAL_DATA_WS_PATH_TEMPLATE.format(**template_vars),
            self.__make_data_handler(connection),
        )

    def __make_serial_get_handler(self, connection: serial.Connection):
        async def handler(request: Request):
            return json_response(
                {
                    "connected": connection.is_connected,
                    "settings": (
                        asdict(connection.current_settings)
                        if connection.current_settings
                        else None
                    ),
                }
            )

        return handler

    def __make_serial_connect_handler(self, connection: serial.Connection):
        async def handler(request: Request):
            try:
                request_data = await request.json()
                new_settings = from_dict(serial.Connection.Settings, request_data)
            except Exception as e:
                raise HTTPBadRequest()

            if connection.current_settings == new_settings:
                raise HTTPNotModified()

            await connection.connect(new_settings)

            return Response(status=200)

        return handler

    def __make_serial_disconnect_handler(self, connection: serial.Connection):
        async def handler(request: Request):
            if not connection.is_connected:
                raise HTTPNotModified()

            await connection.disconnect()
            return Response(status=200)

        return handler

    def __make_data_handler(self, connection: serial.Connection):
        async def handler(request: Request):
            self.logger.debug(
                "New websocket connection received from %s", request.remote
            )
            ws = WebSocketResponse()
            await ws.prepare(request)

            # todo: send small part of history to connected client

            # Register connection
            self.__register_client(ws)

            # Reading
            with connection.multiplexer.connect() as multiplexed_connection:
                writer_task = create_task(
                    self.__send_to_client_task(ws, multiplexed_connection)
                )
                try:
                    async for msg in ws:
                        if msg.type == WSMsgType.ERROR:
                            self.logger.error(
                                "Closing websocket client from %s due to exception: %s",
                                request.remote,
                                ws.exception(),
                            )
                            break
                        elif msg.type == WSMsgType.CLOSE:
                            self.logger.debug(
                                "Closing websocket client from %s with close code: %d",
                                request.remote,
                                ws.close_code,
                            )
                            break
                        elif msg.type == WSMsgType.TEXT:
                            try:
                                await multiplexed_connection.write(
                                    msg.data.encode("utf-8")
                                )
                            except serial.ConnectionLockedError:
                                # Do nothing for now if connection is locked
                                pass
                        else:
                            self.logger.warning(
                                "Received unknown message type on websocket from %s",
                                request.remote,
                            )
                finally:
                    self.__unregister_client(ws)
                    writer_task.cancel()
                    await writer_task

            return ws

        return handler

    async def run(self):
        pass

    async def __send_to_client_task(
        self, ws: WebSocketResponse, connection: serial.MultiplexedConnection
    ):
        try:
            while True:
                data = await connection.read(128)
                if data is None:
                    await connection.wait_until_connected()

                if not data:
                    continue

                await ws.send_bytes(data)
        except CancelledError:
            pass
        except ClientConnectionResetError:
            pass
        except Exception as e:
            self.logger.error("Exception received during sending", exc_info=True)

    def __register_client(self, ws: WebSocketResponse):
        self.logger.debug("Registering websocket client")
        self._active_connections.add(ws)

    def __unregister_client(self, ws: WebSocketResponse):
        self.logger.debug("Unregistering websocket client")
        self._active_connections.remove(ws)
