from dataclasses import dataclass
from typing import List
from asyncio import sleep

from aiohttp.web import Request, json_response, Response
from aiohttp.web_exceptions import HTTPBadRequest, HTTPNotModified
from dacite import from_dict

from selfauto.components.basic_component import BasicComponent
from selfauto.components import webserver, gpio

GPIO_LIST_TEMPLATE = "/api/gpio"
GPIO_PATH_TEMPLATE = f"{GPIO_LIST_TEMPLATE}/{{label}}"
GPIO_TOGGLE_TEMPLATE = f"{GPIO_PATH_TEMPLATE}/toggle"
GPIO_SET_TEMPLATE = f"{GPIO_PATH_TEMPLATE}/set"
GPIO_DOUBLE_TOGGLE_TEMPLATE = f"{GPIO_PATH_TEMPLATE}/double_toggle"


@dataclass
class SetRequestBody:
    value: bool


@dataclass
class DoubleToggleRequestBody:
    delay_ms: int = 100


class GpioHttpComponent(BasicComponent):
    NAME = "gpio_http"

    @dataclass()
    class Config:
        pass

    @staticmethod
    def make_default_config():
        return GpioHttpComponent.Config()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Config = None

    async def on_initialize(self, config: Config):
        self._config = config

        gpio_component: gpio.Component = await self.find_component(gpio.Component)
        webserver_component: webserver.Component = await self.find_component(
            webserver.Component
        )

        webserver_component.add_handler(
            "GET",
            GPIO_LIST_TEMPLATE,
            self.__make_gpio_list(gpio_component),
        )

        for label in gpio_component.labels:
            self.__add_handlers_for(
                label=label,
                ws=webserver_component,
                driver=gpio_component.get_gpio_by_label(label),
            )

    def __add_handlers_for(
        self,
        label: str,
        ws: webserver.Component,
        driver: gpio.BasicGpio,
    ):
        template_vars = {"label": label}

        ws.add_handler(
            "GET",
            GPIO_PATH_TEMPLATE.format(**template_vars),
            self.__make_gpio_get_handler(label, driver),
        )

        ws.add_handler(
            "POST",
            GPIO_SET_TEMPLATE.format(**template_vars),
            self.__make_gpio_set_post_handler(driver),
        )

        ws.add_handler(
            "POST",
            GPIO_TOGGLE_TEMPLATE.format(**template_vars),
            self.__make_gpio_toggle_post_handler(label, driver),
        )

        ws.add_handler(
            "POST",
            GPIO_DOUBLE_TOGGLE_TEMPLATE.format(**template_vars),
            self.__make_gpio_double_toggle_post_handler(label, driver),
        )

    def __make_gpio_list(self, component: gpio.Component):
        async def handler(request: Request):
            return json_response(
                {"gpio": [{"label": label} for label in component.labels]}
            )

        return handler

    def __make_gpio_get_handler(self, label: str, driver: gpio.BasicGpio):
        async def handler(request: Request):
            return json_response(
                {
                    "label": label,
                    "state": await driver.get(),
                }
            )

        return handler

    def __make_gpio_set_post_handler(self, driver: gpio.BasicGpio):
        async def handler(request: Request):
            try:
                request_data = await request.json()
                set_data = from_dict(SetRequestBody, request_data)
            except Exception as e:
                raise HTTPBadRequest()

            current = await driver.get()
            if current == set_data.value:
                raise HTTPNotModified()

            await driver.set(set_data.value)

            return json_response({})

        return handler

    def __make_gpio_toggle_post_handler(self, label: str, driver: gpio.BasicGpio):
        async def handler(request: Request):
            await driver.toggle()

            return json_response(
                {
                    "label": label,
                    "state": await driver.get(),
                }
            )

        return handler

    def __make_gpio_double_toggle_post_handler(
        self, label: str, driver: gpio.BasicGpio
    ):
        async def handler(request: Request):
            try:
                request_data = await request.json()
                data = from_dict(DoubleToggleRequestBody, request_data)
            except Exception as e:
                raise HTTPBadRequest()

            await driver.toggle()
            await sleep(data.delay_ms / 1000)
            await driver.toggle()

            return json_response(
                {
                    "label": label,
                    "state": await driver.get(),
                }
            )

        return handler
