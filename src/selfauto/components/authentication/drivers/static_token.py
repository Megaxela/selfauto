from dataclasses import dataclass
from typing import List, Dict

from selfauto.components.authentication.basic_driver import BasicDriver


class StaticToken(BasicDriver):
    LABEL = "static_token"

    @dataclass
    class Config:
        values: List[str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._values = set()

    async def on_initialize(self, config: Config):
        self._values = set(config.values)

    async def probe(self, auth_data: Dict[str, str]) -> bool:
        return "token" in auth_data

    async def auth(self, auth_data: Dict[str, str]) -> bool:
        return auth_data.get("token") in self._values
