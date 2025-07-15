from dataclasses import dataclass

import aiohttp.web

from selfauto.components.basic_component import BasicComponent


class WebserverComponent(BasicComponent):
    NAME = "webserver"

    @dataclass()
    class Config:
        listen: str
        port: int

    @staticmethod
    def make_default_config():
        return WebserverComponent.Config(listen="127.0.0.1", port=2000)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._app = aiohttp.web.Application()
        self._config: Config = None

    def add_handler(self, method, path, handler):
        self._app.add_routes([getattr(aiohttp.web, method.lower())(path, handler)])

    async def on_initialize(self, config: Config):
        self._config = config

    async def run(self):
        await aiohttp.web._run_app(
            self._app,
            host=self._config.listen,
            port=self._config.port,
            handle_signals=False,
            print=None,
            access_log=self.logger,
        )
