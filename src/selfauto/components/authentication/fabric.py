DRIVER_CLS = {}


def register_driver(driver_cls):
    if not hasattr(driver_cls, "LABEL"):
        raise ValueError(
            "Authentication engine driver should have LABEL attribute to be registered"
        )

    DRIVER_CLS[driver_cls.LABEL] = driver_cls


def get_driver_cls(label: str):
    val = DRIVER_CLS.get(label)
    if val is None:
        raise ValueError(f"Unknown authentication engine driver label '{label}'")

    return val


def list_driver_cls():
    return list(DRIVER_CLS.keys())
