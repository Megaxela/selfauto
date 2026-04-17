from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict

from dacite import from_dict


class BasicDriver(ABC):

    async def initialize(self, config):
        parsed_config = None

        if hasattr(self, "Config"):
            parsed_config = from_dict(self.Config, config)

        await self.on_initialize(parsed_config)

    async def deinitialize(self):
        await self.on_deinitialize()

    @abstractmethod
    async def on_initialize(self, config):
        pass

    async def on_deinitialize(self):
        pass

    @abstractmethod
    async def probe(self, auth_data: Dict[str, str]) -> bool:
        pass

    @abstractmethod
    async def auth(self, auth_data: Dict[str, str]):
        pass
