from dataclasses import dataclass, field
from typing import List, Dict
from logging import getLogger

from selfauto.components.basic_component import BasicComponent

from .config import ConnectionConfig, ModemGPIO
from .connection import Connection


class SerialComponent(BasicComponent):
    NAME = "serial"

    @dataclass()
    class Config:
        connections: List[ConnectionConfig] = field(default_factory=list)

    @staticmethod
    def make_default_config():
        return SerialComponent.Config(
            connections=[
                ConnectionConfig(
                    label="example_conn",
                    path="/dev/ttyUSB0",
                    modem_gpio=ModemGPIO(rts=False),
                )
            ]
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Config = None

        # label -> Connection
        self._connections: Dict[str, Connection] = {}

    @property
    def connection_labels(self):
        return self._connections.keys()

    def get_connection_by_label(self, label: str) -> Connection | None:
        return self._connections.get(label)

    async def on_initialize(self, config: Config):
        self._config = config

        for conn_config in self._config.connections:
            self._connections[conn_config.label] = Connection(
                config=conn_config,
                logger=self.service.make_logger(f"{self.NAME}.{conn_config.label}"),
            )

    async def run(self):
        # todo: Run multiplexer only if config implies, that
        # this connection should be multiplexed.
        for conn in self._connections.values():
            await conn.multiplexer.run()

    async def on_deinitialize(self):
        for conn in self._connections.values():
            await conn.multiplexer.stop()
