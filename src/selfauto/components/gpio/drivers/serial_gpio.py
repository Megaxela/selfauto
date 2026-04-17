from dataclasses import dataclass
from logging import getLogger

from .basic_gpio import BasicGpio

from selfauto.components import serial

TYPE = "serial_gpio"

logger = getLogger(__name__)


class SerialGpio(BasicGpio):
    @dataclass()
    class Config:
        serial_label: str
        signal: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, type_name=TYPE)
        self._connection: serial.Connection | None = None
        self._signal_name: str = None

    async def _on_set(self, value):
        if self._connection is None or self._connection._writer is None:
            return

        setattr(self._connection._writer.transport.serial, self._signal_name, value)

    async def _on_get(self) -> bool:
        if self._connection is None or self._connection._writer is None:
            return False

        return getattr(self._connection._writer.transport.serial, self._signal_name)

    async def _on_initialize(self, config: Config):
        serial_component: serial.Component = await self.parent.find_component(
            serial.Component
        )

        self._connection = serial_component.get_connection_by_label(config.serial_label)

        # if not hasattr(self._connection._transport.serial, config.signal):
        #     raise ValueError(f"Unknown serial signal '{config.signal}'")

        self._signal_name = config.signal
