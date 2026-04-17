from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Tuple
from os.path import join, exists
from os import remove, makedirs
from uuid import uuid4

from aiohttp.web_exceptions import (
    HTTPBadRequest,
    HTTPNotModified,
    HTTPConflict,
    HTTPNotFound,
)
from aiohttp.web import Request, WebSocketResponse, json_response, Response
from aiohttp import MultipartReader, BodyPartReader
from aiohttp.hdrs import CONTENT_TYPE
from dacite import from_dict
from dataclasses import asdict
from aiofiles import open

from selfauto.components.basic_component import BasicComponent
from selfauto.components.tasks import ParameterType, Parameter
from selfauto.components import webserver, tasks

LIST_TASKS_PATH = "/api/tasks"
LIST_RUNNING_TASKS_PATH = "/api/running_tasks"
TASK_INFO_PATH_TEMPLATE = f"{LIST_TASKS_PATH}/{{label}}"
TASK_RUN_PATH_TEMPLATE = f"{TASK_INFO_PATH_TEMPLATE}/run"
RUNNING_TASK_INFO_PATH_TEMPLATE = f"{LIST_RUNNING_TASKS_PATH}/{{task_id}}"


def param_type_to_str(param_type: ParameterType) -> str:
    return {
        ParameterType.FILE: "file",
        ParameterType.STRING: "string",
    }.get(param_type)


@dataclass
class TaskExtraData:
    label: str
    data: dict


class TasksHttpComponent(BasicComponent):
    """
    # List Tasks
    ## Request
    `GET /tasks`

    ## Response
    ```json
    {
      "tasks": [
        {
          "label": "sample_label"
        }
      ]
    }
    ```

    # List Running Tasks
    ## Request
    `GET /running_tasks`

    ## Response
    ```json
    {
      "running_tasks": [
        {
          "id": "running_task_id",
          "label": "label"
        }
      ]
    }
    ```

    # Task Info
    ## Request
    `GET /tasks/{label}`

    ## Response
    ```json
    {
      "label": "{label}",
      "running_tasks": [
        {
          "id": "running_task_id",
          "label": "{label}"
        }
      ],
      "parameters": [
        {
          "name": "filename",
          "type": "file"
        }
      ]
    }
    ```

    # Running Task Info
    ## Request
    `GET /running_tasks/{running_task_id}`

    ## Response
    ```json
    {
      "id": "{running_task_id}",
    }
    ```

    # Run Task
    ## Request
    `POST /tasks/{label}/run`

    ## Response
    ```json
    {
      "id": "{running_task_id}",
    }
    ```

    # Fetch Running Task Logs
    ## Request
    `GET /running_tasks/{running_task_id}/logs`

    ## Response
    Websocket Connection

    # Cancel Running Task
    ## Request
    `POST /running_tasks/{running_task_id}/cancel`

    ## Response
    None

    """

    NAME = "tasks_http"

    @dataclass
    class Config:
        file_download_dir: str
        extra: List[TaskExtraData]

    @staticmethod
    def make_default_config():
        return TasksHttpComponent.Config(
            file_download_dir="/tmp",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._config: Config | None = None
        self.__tasks_component: tasks.Component | None = None
        self.__tasks_extra: Dict[str, dict] = {}

    async def on_initialize(self, config: Config):
        self._config = config
        self.__tasks_extra = {extra.label: extra.data for extra in config.extra}

        webserver_component: webserver.Component = await self.find_component(
            webserver.Component
        )

        self.__tasks_component = await self.find_component(tasks.Component)

        # List Tasks
        webserver_component.add_handler(
            "GET",
            LIST_TASKS_PATH,
            self.__handle_list_tasks,
        )

        # List Running Tasks
        webserver_component.add_handler(
            "GET",
            LIST_RUNNING_TASKS_PATH,
            self.__handle_list_running_tasks,
        )

        # Get Running Task
        webserver_component.add_handler(
            "GET",
            RUNNING_TASK_INFO_PATH_TEMPLATE,
            self.__handle_running_task_info,
        )

        # Task Info
        for label in self.__tasks_component.task_labels:
            self.__add_task_handlers(webserver_component, label)

        # Create temporary file upload directory
        makedirs(self._config.file_download_dir, exist_ok=True)

    async def __handle_list_tasks(self, request: Request):
        return json_response(
            {
                "tasks": [
                    {
                        "label": label,
                    }
                    for label in self.__tasks_component.task_labels
                ]
            }
        )

    async def __handle_list_running_tasks(self, request: Request):
        return json_response(
            {
                "running_tasks": [
                    {"id": task_id, "label": label}
                    for label, task_id in self.__tasks_component.running_task_ids
                ]
            }
        )

    async def __handle_running_task_info(self, request: Request):
        # tbd: make more usefull method
        for label, task_id in self.__tasks_component.running_task_ids:
            if task_id == request.match_info["task_id"]:
                return json_response({})
        raise HTTPNotFound()

    def __add_task_handlers(
        self,
        webserver_component: webserver.Component,
        label: str,
    ):
        template_args = {"label": label}

        TASK_PATH = TASK_INFO_PATH_TEMPLATE.format(**template_args)
        TASK_RUN_PATH = TASK_RUN_PATH_TEMPLATE.format(**template_args)

        task_cls_data = self.__tasks_component.task_cls_data_by_label(label)

        # Task Info
        webserver_component.add_handler(
            "GET",
            TASK_PATH,
            self.__make_task_info_handler(label, task_cls_data),
        )

        # Run Task
        webserver_component.add_handler(
            "POST",
            TASK_RUN_PATH,
            self.__make_task_run_handler(label, task_cls_data),
        )

        # todo: run handlers at least

    def __make_task_info_handler(self, label: str, task_cls: tasks.TaskClsData):
        async def handler(request: Request):

            return json_response(
                {
                    "label": label,
                    "exclusive": task_cls.exclusive,
                    "running_tasks": [
                        {
                            "id": task_id,
                            "label": task_label,
                        }
                        for task_label, task_id in filter(
                            lambda x: x[0] == label,
                            self.__tasks_component.running_task_ids,
                        )
                    ],
                    "parameters": [
                        {
                            "name": parameter.name,
                            "type": param_type_to_str(parameter.type),
                        }
                        for parameter in task_cls.cls.PARAMETERS
                    ],
                    "extra": self.__tasks_extra.get(label),
                }
            )

        return handler

    def __make_task_run_handler(self, label: str, task_cls: tasks.TaskClsData):
        async def handler(request: Request):
            clear_cbs = []

            try:
                parameters = {}

                # Handle task parameters
                if hasattr(task_cls.cls, "PARAMETERS") and task_cls.cls.PARAMETERS:
                    # Convert parameters to map
                    task_params_map = {
                        param.name: param for param in task_cls.cls.PARAMETERS
                    }

                    reader = await request.multipart()

                    # Reading parameters
                    while True:
                        part = await reader.next()

                        if part is None:
                            break

                        # Check parameter
                        if part.name not in task_params_map:
                            if part.name in parameters:
                                raise HTTPBadRequest(
                                    reason=f"Multiple task parameter '{part.name}' provided"
                                )
                            else:
                                raise HTTPBadRequest(
                                    reason=f"Unknown task parameter '{part.name}'"
                                )

                        parameters[part.name], clear_cb = (
                            await self.__handle_multipart_parameter(
                                task_params_map[part.name], part
                            )
                        )
                        clear_cb = None

                        if clear_cb is not None:
                            clear_cbs.append(clear_cb)

                        # Remove parameter from dict of pending parameters
                        del task_params_map[part.name]

                    if task_params_map:
                        raise HTTPBadRequest(
                            reason=f"Missing task parameters: {', '.join(task_params_map.keys())}"
                        )

                try:
                    running_task = await self.__tasks_component.run_task(
                        label, parameters
                    )
                except tasks.exceptions.AlreadyRunningError:
                    raise HTTPConflict(f"Exclusive task '{label}' is already running")

                # We do not have to clear, because we successfully finished running task.
                # Leaving resource management to it.
                clear_cbs = []
                return json_response(
                    {
                        "id": running_task.id,
                        "label": label,
                    }
                )
            finally:
                for clear_cb in clear_cbs:
                    await clear_cb()

        return handler

    async def __handle_multipart_parameter(
        self,
        parameter: Parameter,
        part: BodyPartReader | MultipartReader,
    ) -> Tuple[Any, Callable]:
        def make_remove_file_cleaner(path: str):
            async def clean():
                if exists(path):
                    remove(path)

        match parameter.type:
            case ParameterType.FILE:
                # File can be uploaded as file
                # or can be provided with URL that
                # should be downloaded.
                match part.headers.get(CONTENT_TYPE):
                    case "application/octet-stream":
                        result_file_path = join(
                            self._config.file_download_dir,
                            f"{part.filename}_{uuid4().hex}",
                        )

                        # Downloading file to temp directory

                        async with open(result_file_path, "wb") as f:
                            while True:
                                chunk = await part.read_chunk()
                                if not chunk:
                                    break
                                await f.write(chunk)

                        return result_file_path, make_remove_file_cleaner(
                            result_file_path
                        )
                    case "text/plain":
                        value = await part.read(decode=True)
                        if not any(
                            (
                                value.startswith("http://"),
                                value.startswith("https://"),
                            )
                        ):
                            raise HTTPBadRequest(
                                reason=f"Parameter '{parameter.name}' should be file upload or url"
                            )

                        return value, None

                raise RuntimeError(
                    f"Unknown file content-type '{part.headers.get(CONTENT_TYPE)} for part'"
                )

            case ParameterType.STRING:
                return await part.read(decode=True), None

        raise RuntimeError(f"Unknown parameter type '{parameter.type}'")

    async def run(self):
        pass
