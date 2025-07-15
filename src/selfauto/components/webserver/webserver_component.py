import dataclasses
from typing import List

import aiohttp.web

from selfauto.components.basic_component import BasicComponent
from .basic_middleware import BasicMiddleware


class WebserverComponent(BasicComponent):
    NAME = "webserver"

    @dataclasses.dataclass()
    class Config:
        listen: str
        port: int

    @staticmethod
    def make_default_config():
        return WebserverComponent.Config(listen="127.0.0.1", port=2000)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._app = aiohttp.web.Application()
        self._middlewares: List[BasicMiddleware] = []
        self._config: Config = None

    def add_middleware(self, middleware: BasicMiddleware):
        self._middlewares.append(middleware)

    def add_handler(self, method, path, handler):
        self._app.add_routes(
            [getattr(aiohttp.web, method.lower())(path, self.__make_handler(handler))]
        )

    async def on_initialize(self, config: Config):
        self._config = config

    async def run(self):
        await aiohttp.web._run_app(
            self._app,
            host=self._config.listen,
            port=self._config.port,
            handle_signals=False,
            print=None,
        )

    def __make_handler(self, actual_handler):
        async def handler(request: aiohttp.web.Request):
            response = None
            try:
                # 1. Executing before request middlewares
                for mw in self._middlewares:
                    await mw.on_before_request(request)

                # 2. Actually executing handler
                response = await actual_handler(request)

            except Exception as e:
                # 3. If error acquired - handle it and rethrow
                for mw in self._middlewares:
                    await mw.on_error(request, e)

                raise e

            finally:
                # ??. Executing after request middlewares
                for mw in self._middlewares:
                    await mw.on_after_request(request, response)

            return response

        return handler
