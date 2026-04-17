from selfauto.components.events import BasicEvent


class TaskStarted(BasicEvent):
    ID = "task_started"

    def __init__(self, task_id: str):
        super().__init__()
        self.__task_id = task_id

    @property
    def json_data(self):
        return {
            "task_id": self.__task_id,
        }
