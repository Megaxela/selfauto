from logging import Handler, LogRecord, NOTSET
from typing import Dict, List


class LogStorage:
    def __init__(self):
        # task_id -> list[LogRecord]
        self.__active_logs: Dict[str, List[LogRecord]] = {}

    def make_log_handler_for(self, task_id):
        class LogHandlerManager:
            def __init__(self, storage):
                self.__storage = storage

            async def __aenter__(self, *args, **kwargs):
                class LogHandler(Handler):
                    def __init__(self, storage):
                        super().__init__(NOTSET)
                        self.__storage = storage

                    def emit(self, record: LogRecord):
                        self.__storage._push_log_for(task_id, record)

                return LogHandler(self.__storage)

            async def __aexit__(self, *args, **kwargs):
                # Perform committing of current task id logs
                pass

    def _push_log_for(self, task_id, record: LogRecord):
        logs_list = self.__active_logs.setdefault(task_id, list())

        # We are assuming that logs are always sequential
        logs_list.append(task_id)

    async def _commit_task_logs(self, task_id):
        pass

    async def fetch_logs_for(self, task_id, since_time, until_time, amount):
        pass
