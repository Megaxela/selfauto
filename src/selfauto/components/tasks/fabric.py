TASK_CLS = {}


def register_task(task_cls):
    if not hasattr(task_cls, "LABEL"):
        raise ValueError("Task should have LABEL attribute to be registered")

    TASK_CLS[task_cls.LABEL] = task_cls


def get_task_cls(label: str):
    val = TASK_CLS.get(label)
    if val is None:
        raise ValueError(f"Unknown task label '{label}'")

    return val


def list_task_cls():
    return list(TASK_CLS.keys())
