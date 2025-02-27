import asyncio
import argparse
import logging
import os
import dataclasses

import aiohttp

from selfauto.service import Service
from selfauto.config import Config

from selfauto.components import webserver
from selfauto.components.basic_component import BasicComponent

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MyComponent(BasicComponent):
    NAME = "my_component"

    @dataclasses.dataclass()
    class Config:
        hello_text: str

        @staticmethod
        def make_default():
            return Config(hello_text="Hello")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hello_text: str = None

    async def on_initialize(self, config: Config):
        self._hello_text = config.hello_text
        logger.info("Hello %s", self._hello_text)

        webserver_component: webserver.Component = await self.find_component(
            webserver.Component
        )
        webserver_component.add_handler("GET", "/hello_request", self.__on_request)

    async def __on_request(self, request):
        return aiohttp.web.json_response({"Hello": self._hello_text})

    async def run(self):
        while True:
            logger.info("Hello again %s", self._hello_text)
            await asyncio.sleep(1)


def parse_args():
    args = argparse.ArgumentParser()

    args.add_argument("--config", type=str, required=True)

    return args.parse_args()


async def main(args):
    config = Config.load_from_file(args.config)

    service = Service(config)

    service.add_components(
        [
            database.Component,
            webserver.Component,
            MyComponent,
        ]
    )

    await service.run()


if __name__ == "__main__":
    asyncio.new_event_loop().run_until_complete(main(parse_args()))
