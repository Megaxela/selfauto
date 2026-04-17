from abc import ABC, abstractmethod

from dacite import from_dict

from selfauto.components.basic_component import BasicComponent


class BasicGpio:
    def __init__(self, parent, type_name):
        self.__type_name = type_name
        self.__initialized = False
        self.__parent = parent

    @property
    def parent(self) -> BasicComponent:
        return self.__parent

    async def set(self, value: bool):
        await self._on_set(value)

    async def get(self):
        return await self._on_get()

    async def toggle(self):
        await self.set(not await self.get())

    async def initialize(self, config: dict):
        if self.__initialized:
            return
        await self._on_initialize(from_dict(type(self).Config, config))
        self.__initialized = True

    @abstractmethod
    async def _on_set(self, value):
        pass

    @abstractmethod
    async def _on_get(self) -> bool:
        pass

    @abstractmethod
    async def _on_initialize(self):
        pass
