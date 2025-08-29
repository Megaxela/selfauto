from asyncio import sleep, new_event_loop
from argparse import ArgumentParser
from logging import getLogger, DEBUG
from dataclasses import dataclass
import os

from aiohttp.web import json_response

from selfauto.service import Service
from selfauto.config import Config

from selfauto.components import webserver
from selfauto.components.basic_component import BasicComponent


class MyComponent(BasicComponent):
    NAME = "my_component"

    @dataclass()
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
        self.logger.info("Hello %s", self._hello_text)

        webserver_component: webserver.Component = await self.find_component(
            webserver.Component
        )
        webserver_component.add_handler("GET", "/hello_request", self.__on_request)

    async def __on_request(self, request):
        return json_response({"Hello": self._hello_text})

    async def run(self):
        while True:
            self.logger.info("Hello again %s", self._hello_text)
            await sleep(1)


def parse_args():
    args = ArgumentParser()

    args.add_argument("--config", type=str, required=True)

    return args.parse_args()


async def main(args):
    config = Config.load_from_file(args.config)

    def logger_factory(name: str):
        new_logger = getLogger(name)

        if name == MyComponent.NAME:
            new_logger.setLevel(DEBUG)

        return new_logger

    service = Service(config, logger_factory)

    service.add_components(
        [
            database.Component,
            webserver.Component,
            MyComponent,
        ]
    )

    await service.run()


if __name__ == "__main__":
    new_event_loop().run_until_complete(main(parse_args()))
