import logging
import asyncio
import typing as tp
import signal
import dataclasses

import yaml
import dacite
import aiofiles

from selfauto.config import Config
from selfauto.components.basic_component import BasicComponent
from selfauto.utils.asyncio import check_tasks_results_error

logger = logging.getLogger(__name__)


class Service:
    def __init__(self):
        self._components: tp.Dict[str, BasicComponent] = {}
        self._tasks = []

    def add_components(self, cls_list):
        for c in cls_list:
            self.add_component(c)

    def add_component(self, cls):
        if not hasattr(cls, "NAME"):
            raise ValueError(f"Component '{cls}' has no NAME property")

        if cls.NAME in self._components:
            raise RuntimeError(f"Component '{cls.NAME}' is already registered")

        self._components[cls.NAME] = cls(self._components)

    def __register_interrupt_handler(self):
        loop = asyncio.get_event_loop()

        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(s, lambda: asyncio.create_task(self.stop()))

    async def generate_default_config(self, path: str):
        config = Config(
            components={
                component_name: type(component).make_default_config()
                for component_name, component in self._components.items()
                if hasattr(type(component), "Config")
                if hasattr(type(component), "make_default_config")
            }
        )

        async with aiofiles.open(path, "w") as f:
            await f.write(yaml.dump({"config": dataclasses.asdict(config)}))

    async def stop(self):
        logging.info("Stopping execution")
        for t in self._tasks:
            t.cancel()

    async def run(self, config: Config):
        self.__register_interrupt_handler()

        # Initializing
        try:
            logger.info("Initializing component")
            self._tasks = []
            for name, component in self._components.items():
                self._tasks.append(
                    asyncio.create_task(
                        self._initialize_component(component, config),
                        name=f"{name}-initialize",
                    )
                )

            if not await check_tasks_results_error(
                await asyncio.gather(*self._tasks, return_exceptions=True)
            ):
                return

            # Running
            logger.info("Initialization finished. Running components")
            self._tasks = []
            for name, component in self._components.items():
                self._tasks.append(
                    asyncio.create_task(
                        self._run_component(component), name=f"{name}-run"
                    )
                )

            if not await check_tasks_results_error(
                await asyncio.gather(*self._tasks, return_exceptions=True)
            ):
                return
        finally:
            logger.info("Deinitializing component")
            self._tasks = []
            for name, component in self._components.items():
                self._tasks.append(
                    asyncio.create_task(
                        self._deinitialize_component(component),
                        name=f"{name}-deinitialize",
                    )
                )

            if not await check_tasks_results_error(
                await asyncio.gather(*self._tasks, return_exceptions=True)
            ):
                return

    async def _initialize_component(self, component, config):
        component_config = None
        try:
            if hasattr(type(component), "Config"):
                component_name = type(component).NAME
                if component_name not in config.components:
                    raise RuntimeError(
                        f"No component '{component_name}' config in config file"
                    )

                component_config = dacite.from_dict(
                    type(component).Config,
                    config.components[component_name],
                )

            await component.initialize(component_config)
        except Exception as e:
            logger.error(
                "Received exception during initialization of '%s' component",
                type(component).NAME,
                exc_info=e,
            )
            raise

    async def _deinitialize_component(self, component):
        try:
            await component.deinitialize()
        except Exception as e:
            logger.error(
                "Received exception during deinitialization of '%s' component",
                type(component).NAME,
                exc_info=e,
            )
            await self.stop()

    async def _run_component(self, component):
        try:
            await component.run()
        except asyncio.exceptions.CancelledError:
            return
        except Exception as e:
            logger.error(
                "Received exception running '%s' component",
                type(component).NAME,
                exc_info=e,
            )
            await self.stop()
