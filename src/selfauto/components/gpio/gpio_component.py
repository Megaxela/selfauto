from dataclasses import dataclass, field
from typing import List, Dict

from selfauto.components.basic_component import BasicComponent

from .drivers.basic_gpio import BasicGpio
from .drivers import serial_gpio

GPIO_DRIVERS = {
    serial_gpio.TYPE: serial_gpio.SerialGpio,
}


def build_gpio(parent: BasicComponent, type_name: str) -> BasicGpio:
    cls = GPIO_DRIVERS.get(type_name)
    if cls is None:
        raise ValueError(
            f"Unknown GPIO driver '{type_name}'. Available values: [{', '.join(GPIO_DRIVERS.keys())}]"
        )

    return cls(parent=parent)


@dataclass()
class GpioConfig:
    label: str
    driver: str
    config: Dict


class GpioComponent(BasicComponent):
    NAME = "gpio"

    @dataclass()
    class Config:
        gpios: List[GpioConfig] = field(default_factory=list)

    @staticmethod
    def make_default_config():
        return GpioComponent.Config(
            gpios=[
                GpioConfig(
                    label="example_gpio",
                    driver="serial_gpio",
                    config={
                        "serial_label": "example_serial",
                        "signal": "rts",
                    },
                )
            ]
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Config = None

        # label -> Gpio
        self._gpios: Dict[str, BasicGpio] = {}

    @property
    def labels(self):
        return list(self._gpios.keys())

    def get_gpio_by_label(self, label: str) -> BasicGpio | None:
        return self._gpios.get(label)

    async def on_initialize(self, config: Config):
        self._config = config

        for gpio_config in self._config.gpios:
            gpio = build_gpio(self, gpio_config.driver)
            self._gpios[gpio_config.label] = gpio
            await gpio.initialize(gpio_config.config)
