from logging import Logger
from asyncio import (
    Condition,
    Protocol,
    StreamReaderProtocol,
    run_coroutine_threadsafe,
    get_event_loop,
)

import serial_asyncio


class ProxyStreamReaderProtocol(StreamReaderProtocol):
    def __init__(self, *args, connected_condvar: Condition, logger: Logger, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logger
        self._connected = False
        self._connection_cond_var: Condition = connected_condvar

    @property
    def logger(self):
        return self._logger

    def connection_made(self, *args, **kwargs):
        self.logger.debug("Received connection_made event")
        super().connection_made(*args, **kwargs)
        self._connected = True

        # Spawn coroutine
        run_coroutine_threadsafe(self.__notify_connected(), get_event_loop())

    def connection_lost(self, *args, **kwargs):
        self.logger.debug("Received connection_lost event")
        super().connection_lost(*args, **kwargs)
        self._connected = False

    # async def wait_for_connection_made(self):
    #     logger.debug("Waiting for connection made")
    #     while not self._connected:
    #         logger.debug("Waiting for connection")
    #         async with self._connection_cond_var:
    #             await self._connection_cond_var.wait()

    async def __notify_connected(self):
        self.logger.debug("Acquiring connection condvar")
        async with self._connection_cond_var:
            self.logger.debug("Notifying connection condvar")
            self._connection_cond_var.notify_all()
