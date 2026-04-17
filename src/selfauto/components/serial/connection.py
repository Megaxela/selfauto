from asyncio import (
    get_event_loop,
    Semaphore,
    wait_for,
    StreamWriter,
    StreamReader,
    Condition,
)
from serial_asyncio import open_serial_connection, create_serial_connection
from dataclasses import dataclass
from logging import Logger
from time import time

from .config import ConnectionConfig
from .protocol import ProxyStreamReaderProtocol
from .multiplexer import Multiplexer


async def make_serial_connection(reader, protocol, **kwargs):
    loop = get_event_loop()

    transport, _ = await create_serial_connection(
        loop, protocol_factory=lambda: protocol, **kwargs
    )
    return StreamWriter(transport, protocol, reader, loop)


class Connection:
    @dataclass()
    class Settings:
        baudrate: int

    def __init__(self, config: ConnectionConfig, logger: Logger):
        self._config: ConnectionConfig = config
        self._current_settings: Connection.Settings | None = None
        self._logger = logger

        self._lock_semaphore = Semaphore(1)

        self._multiplexer: Multiplexer = Multiplexer(
            connection=self,
            logger=self._logger,
        )
        self._writer: StreamWriter | None = None
        self._reader: StreamReader | None = None

        # self._protocol: ProxyStreamReaderProtocol = ProxyStreamReaderProtocol(
        #     self._reader
        # )

        self._connected_condvar = Condition()
        self._protocol: ProxyStreamReaderProtocol | None = None

    @property
    def logger(self):
        return self._logger

    async def __aenter__(self):
        await self._lock_semaphore.acquire()
        return self

    async def __aexit__(self, *args):
        self._lock_semaphore.release()

    @property
    def is_connected(self) -> bool:
        return self._writer is not None

    @property
    def current_settings(self) -> "Settings":
        if self.is_connected:
            return self._current_settings
        return None

    @property
    def multiplexer(self) -> Multiplexer:
        return self._multiplexer

    def supports_speed(self, speed: int):
        # If support list is not specified - assuming that it's
        # supported.
        if self._config.supported_speeds is None:
            return True

        return speed in self._config.supported_speeds

    async def connect(self, settings: "Settings"):
        if self.is_connected:
            self.logger.info(
                "Reconnecting to '%s' with new settings '%s'",
                self._config.label,
                settings,
            )
            # tbd: test to check does pyserial
            # allows switching baudrates in runtime
            self._current_settings = settings

            if not self.supports_speed(self._current_settings.baudrate):
                self.logger.warning(
                    "Trying to reconnect '%s' with explicitly unsupported speed '%d'",
                    self._config.label,
                    settings.baudrate,
                )

            self._writer.transport.serial.baudrate = settings.baudrate

        self.logger.info(
            "Connecting to '%s' with settings '%s'", self._config.label, settings
        )
        self._current_settings = settings

        if not self.supports_speed(self._current_settings.baudrate):
            self.logger.warning(
                "Trying to connect '%s' with explicitly unsupported speed '%d'",
                self._config.label,
                settings.baudrate,
            )

        self._reader = StreamReader(
            limit=1 * 1024 * 1024,  # 1MB
        )

        self._protocol = ProxyStreamReaderProtocol(
            self._reader,
            connected_condvar=self._connected_condvar,
            logger=self.logger,
        )

        self._writer = await make_serial_connection(
            reader=self._reader,
            protocol=self._protocol,
            url=self._config.path,
            baudrate=settings.baudrate,
            do_not_open=True,
        )

        if self._config.modem_gpio.rts:
            self._writer.transport.serial.rts = False

        self._writer.transport.serial.open()

        await self.wait_until_connected()

    async def disconnect(self):
        if not self.is_connected:
            return

        self.logger.info("Disconnecting '%s'", self._config.label)
        await self._writer.drain()
        self._writer.close()
        self._protocol = None
        self._writer = None

    async def wait_until_connected(self):
        while self._protocol is None or not self._protocol._connected:
            async with self._connected_condvar:
                await self._connected_condvar.wait()
        # await self._protocol.wait_for_connection_made()

    # note: all 'read*' methods are exclusive for user.
    # multiplexed IO is much more preferred for
    # connection usage.
    async def read_line(self):
        if not self.is_connected:
            return None
        return await self._reader.readline()

    async def readuntil(self, separator):
        if not self.is_connected:
            return None
        buff = await self._reader.readuntil(separator)

        return buff

    async def read_for(self, seconds):
        if not self.is_connected:
            return None

        buff = bytes()

        start_time = time()

        while start_time + seconds > time():
            try:
                read_byte = await wait_for(self.read(1), time() - start_time)
            except TimeoutError:
                continue

            buff += read_byte

        return buff

    async def read(self, amount=None):
        if not self.is_connected:
            return None

        if amount is None:
            return await self._reader.read()

        return await self._reader.read(amount)

    async def write(self, data: bytes):
        if not self.is_connected:
            return

        self._writer.write(data)
        await self._writer.drain()
