# selfauto
This project is the implementation of a framework for my services for various automation. 

This project implements a component architecture. 
The API of the components may change, since this is a purely pet project.

## Supported Components
### `webserver`
A component that provides a HTTP web server for other components.

#### Config
```yaml
listen: 0.0.0.0 # IP address to listen on
port: 8888      # TCP port to listen on
```

### `database`
A component that provides database for other components. Currently it only supports sqlite, but in the future it might be able to use other databases.

#### Config
```yaml
path: ./db.sqlite # Path to sqlite database
```

### `telegram`
A component, that provides telegram bot API for other components.

#### Config
```yaml
bot_token: <token> # Token for telegram bot
```

## Usage
### `main.py`
```python
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

```

### `config.yaml`
```yaml
config:
  components:
    webserver:
      listen: 0.0.0.0
      port: 8888

    database:
      path: ./db.sqlite

    my_component:
      hello_text: 'example_text'

```

## License
Library is licensed under the [MIT License](https://opensource.org/licenses/MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
