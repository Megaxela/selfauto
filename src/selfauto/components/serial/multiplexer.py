from typing import Set
from asyncio import Task, create_task, sleep
from logging import Logger

from .multiplexed_connection import MultiplexedConnection


class Multiplexer:
    def __init__(self, connection: "Connection", logger: Logger):
        self._logger = logger
        self._mux_connections: Set[MultiplexedConnection] = set()
        self._connection: "Connection" = connection
        self._read_task: Task | None = None
        self._exclusive_mux_connection: MultiplexedConnection | None = None

    @property
    def logger(self) -> Logger:
        return self._logger

    def connect(self) -> MultiplexedConnection:
        new_conn = MultiplexedConnection(self)

        self.register(new_conn)

        return new_conn

    def register(self, conn: MultiplexedConnection):
        self.logger.debug(
            "Registering new multiplexed connection (total: %d)",
            len(self._mux_connections),
        )
        self._mux_connections.add(conn)

    def unregister(self, conn: MultiplexedConnection):
        self.logger.debug(
            "Unregistering new multiplexed connection (total: %d)",
            len(self._mux_connections),
        )
        if self._exclusive_mux_connection == conn:
            self._exclusive_mux_connection = None
        self._mux_connections.remove(conn)

    async def stop(self):
        self.logger.debug("Stopping multiplexer processing")
        if self._read_task is not None:
            self._read_task.cancel("Stop requested")
            await self._read_task

    async def run(self):
        self.logger.debug("Running multiplexer processing")
        if self._read_task is not None:
            raise RuntimeError("Multiplexer is already running")

        self._read_task = create_task(self.__read_worker())

    async def __read_worker(self):
        while True:
            data = await self._connection.read(128)
            if data is None:  # Connection is not active
                await self._connection.wait_until_connected()

            if not data:
                continue

            for mux in self._mux_connections:
                mux.feed_data(data)
