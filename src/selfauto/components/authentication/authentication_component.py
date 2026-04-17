from dataclasses import dataclass
from typing import List, Any, Dict

from selfauto.components.basic_component import BasicComponent

from .basic_driver import BasicDriver
from .fabric import get_driver_cls, register_driver
from .authentication_engine import AuthenticationEngine
from .drivers.static_token import StaticToken


@dataclass
class EngineConfig:
    label: str
    driver: str
    config: Any


class AuthenticationComponent(BasicComponent):
    NAME = "authentication"

    @dataclass
    class Config:
        engines: List[EngineConfig]

    @staticmethod
    def make_default_config():
        return AuthenticationComponent.Config(
            engines=[
                EngineConfig(label="token_1", driver="token"),
                EngineConfig(label="token_2", driver="token"),
            ]
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Register default authentication drivers
        register_driver(StaticToken)

        self._config: Config = None

        # label -> AuthenticationEngine
        self._engines: Dict[str, AuthenticationEngine] = {}

    async def authenticate(self, auth_data: Dict[str, str]):
        for engine in self._engines.values():
            if await engine.authenticate(auth_data):
                return True
        return False

    def get_engine(self, label) -> AuthenticationEngine | None:
        return self._engines.get(label)

    async def on_initialize(self, config: Config):
        self._config = config

        # Instantiating authentication engines with proper drivers
        for engine_config in config.engines:
            if engine_config.label in self._engines:
                raise ValueError(
                    f"Multiple authentication engines with same label presented. Label: '{engine_config.label}'"
                )

            self._engines[engine_config.label] = AuthenticationEngine(
                label=engine_config.label,
                driver=get_driver_cls(engine_config.driver)(),
                driver_config=engine_config.config,
            )

        # Initializing drivers
        for authentication_engine in self._engines.values():
            await authentication_engine.initialize()

    async def on_deinitialize(self):
        for authentication_engine in self._engines.values():
            await authentication_engine.deinitialize()

    async def run(self):
        pass  # do nothing for now
