import logging
import dataclasses
import asyncio

import aiosqlite

from selfauto.components.basic_component import BasicComponent

logger = logging.getLogger(__name__)


class DatabaseComponent(BasicComponent):
    NAME = "database"

    @dataclasses.dataclass()
    class Config:
        path: str

        @staticmethod
        def make_default():
            return Config(path="./db.sqlite")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._connection: aiosqlite.Connection = None
        self._semaphore = asyncio.Semaphore(1)

    async def on_initialize(self, config: Config):
        logger.info("Connecting to database")
        self._connection = await aiosqlite.connect(config.path)
        logger.info("Connected")

    async def on_deinitialize(self):
        await self._connection.close()

    async def run(self):
        while True:
            await asyncio.sleep(1)

    async def __aenter__(self, *args, **kwargs):
        await self._semaphore.acquire()
        return self

    async def __aexit__(self, *args, **kwargs):
        self._semaphore.release()

    async def execute_script(self, query):
        return await self._connection.executescript(query)

    async def execute(self, query, parameters=None):
        return await self._connection.execute(query, parameters)

    async def execute_fetchall(self, query, parameters=None):
        return await self._connection.execute_fetchall(query, parameters)

    async def commit(self):
        await self._connection.commit()
