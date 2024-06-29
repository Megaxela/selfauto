import abc
import asyncio
import logging
import inspect
import os

import aiofiles

logger = logging.getLogger(__name__)


class BasicComponent(abc.ABC):
    def __init__(self, components):
        self._components = components
        self._initialized = False
        self._initialized_condvar = asyncio.Condition()

    async def wait_for_initialization(self):
        async with self._initialized_condvar:
            await self._initialized_condvar.wait_for(lambda: self._initialized)

    async def find_component(self, component):
        if isinstance(component, str):
            component = self._components.get(component)
        else:
            component = self._components.get(component.NAME)

        if component is None:
            return None

        logger.info(
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

    @abc.abstractmethod
    async def on_initialize(self, config):
        pass

    async def on_deinitialize(self):
        pass
