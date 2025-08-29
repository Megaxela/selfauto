from dataclasses import dataclass
from asyncio import Lock, sleep
from typing import List, Dict

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine

from selfauto.components.basic_component import BasicComponent


@dataclass
class ConnectionConfig:
    label: str
    uri: str


@dataclass
class EngineContext:
    label: str
    engine: AsyncEngine
    meta: MetaData


class DatabaseComponent(BasicComponent):
    NAME = "database"

    @dataclass()
    class Config:
        connections: List[ConnectionConfig]

    @staticmethod
    def make_default_config():
        return DatabaseComponent.Config(
            connections=[
                ConnectionConfig(
                    label="ram_sqlite",
                    uri="sqlite+aiosqlite://",
                )
            ]
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._engines: Dict[str, EngineContext] = {}

    async def on_initialize(self, config: Config):
        for conn_conf in config.connections:
            self.logger.info("Creating '%s' database engine", conn_conf.label)
            self._engines[conn_conf.label] = EngineContext(
                label=conn_conf.label,
                engine=create_async_engine(conn_conf.uri),
                meta=MetaData(),
            )

    async def on_post_initialize(self):
        for engine_info in self._engines.values():
            self.logger.info("Initializing '%s' database engine")
            async with engine_info.engine.begin() as conn:
                await conn.run_sync(engine_info.meta.create_all)

    async def on_deinitialize(self):
        await self._connection.close()

    async def run(self):
        # Run initial
        pass

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
