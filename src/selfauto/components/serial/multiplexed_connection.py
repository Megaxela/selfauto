from asyncio import Condition, StreamReader, wait_for
from time import time
from logging import Logger


class ConnectionLockedError(Exception):
    pass


class WriteLock:
    def __init__(self, conn: "MultiplexedConnection", multiplexer: "Multiplexer"):
        self._multiplexer = multiplexer
        self._conn = conn

    def __enter__(self):
        self._multiplexer._exclusive_mux_connection = self._conn
        return self

    def __exit__(self, *args, **kwargs):
        self._multiplexer._exclusive_mux_connection = None


class MultiplexedConnection(StreamReader):
    def __init__(self, multiplexer: "Multiplexer"):
        super().__init__(limit=1 * 1024 * 1024)
        self._data_received_condition = Condition()
        self._multiplexer: "Multiplexer" = multiplexer

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self._multiplexer.unregister(self)

    def lock_writing(self):
        return WriteLock(self, self._multiplexer)

    def supports_speed(self, speed: int):
        return self._multiplexer._connection.supports_speed(speed)

    async def wait_until_connected(self):
        await self._multiplexer._connection.wait_until_connected()

    async def write(self, data: bytes):
        if self._multiplexer._exclusive_mux_connection:
            if self._multiplexer._exclusive_mux_connection != self:
                raise ConnectionLockedError()

        await self._multiplexer._connection.write(data)

    async def connect(self, *args, **kwargs):
        return await self._multiplexer._connection.connect(*args, **kwargs)

    async def disconnect(self):
        return await self._multiplexer._connection.disconnect()

    async def read_for(self, seconds):
        if not self.is_connected:
            return None

        buff = bytes()

        start_time = time()

        while start_time + seconds > time():
            try:
                read_byte = await wait_for(self.read(128), time() - start_time)
            except TimeoutError:
                continue

            buff += read_byte

        return buff

    @property
    def current_settings(self):
        return self._multiplexer._connection.current_settings

    @property
    def is_connected(self):
        return self._multiplexer._connection.is_connected
