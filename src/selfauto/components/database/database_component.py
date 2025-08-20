from dataclasses import dataclass
from asyncio import Lock, sleep

from aiosqlite import Connection, connect

from selfauto.components.basic_component import BasicComponent


class DatabaseComponent(BasicComponent):
    NAME = "database"

    @dataclass()
    class Config:
        path: str

    @staticmethod
    def make_default_config():
        return DatabaseComponent.Config(path="./db.sqlite")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._connection: Connection = None
        self._semaphore: Lock = Lock()

    async def on_initialize(self, config: Config):
        self.logger.info("Connecting to database")
        self._connection = await aiosqlite.connect(config.path)
        self.logger.info("Connected")

    async def on_deinitialize(self):
        await self._connection.close()

    async def run(self):
        while True:
            await sleep(1)

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
