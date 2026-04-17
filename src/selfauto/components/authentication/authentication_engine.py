from dataclasses import dataclass
from typing import Dict, Any

from .basic_driver import BasicDriver


@dataclass
class AuthenticationEngine:
    label: str
    driver: BasicDriver
    driver_config: Any

    async def authenticate(self, auth_data: Dict[str, str]) -> bool:
        if not await self.driver.probe(auth_data):
            return False

        return await self.driver.auth(auth_data)

    async def initialize(self):
        await self.driver.initialize(self.driver_config)

    async def deinitialize(self):
        await self.driver.deinitialize()
