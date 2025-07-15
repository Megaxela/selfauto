from abc import ABC, abstractmethod
from typing import Dict
from logging import Logger
from asyncio import Condition
import inspect
import os

import aiofiles


class BasicComponent(ABC):
    def __init__(
        self,
        components: Dict[str, "BasicComponent"],
        logger: Logger,
        service: "Service",
    ):
        self._components: Dict[str, "BasicComponent"] = components
        self._initialized: bool = False
        self._initialized_condvar: Condition = Condition()
        self._logger: Logger = logger
        self._service = service

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def service(self) -> "Service":
        return self._service

    async def wait_for_initialization(self):
        async with self._initialized_condvar:
            await self._initialized_condvar.wait_for(lambda: self._initialized)

    async def find_component(self, component) -> "BasicComponent":
        component_name = None
        if isinstance(component, str):
            component_name = component
        else:
            component_name = component.NAME

        component = self._components.get(component_name)

        if component is None:
            self.logger.error(
                "Unable to find component '%s'",
                component_name,
            )
            return None

        self.logger.info(
            "Fetching component to '%s' <- '%s'",
            type(self).NAME,
            type(component).NAME,
        )

        await component.wait_for_initialization()

        return component

    async def read_asset(self, path: str) -> bytes:
        async with aiofiles.open(
            os.path.join(self.__make_assets_path(), path), "r"
        ) as f:
            return await f.read()

    def list_assets(self, path: str):
        return os.listdir(os.path.join(self.__make_assets_path(), path))

    def __make_assets_path(self):
        path = os.path.split(inspect.getfile(type(self)))[0]
        return os.path.join(path, "assets")

    async def initialize(self, *args, **kwargs):
        await self.on_initialize(*args, **kwargs)
        self._initialized = True

        async with self._initialized_condvar:
            self._initialized_condvar.notify_all()

    async def deinitialize(self):
        await self.on_deinitialize()

    async def run(self):
        pass

    @abstractmethod
    async def on_initialize(self, config):
        pass

    async def on_deinitialize(self):
        pass
