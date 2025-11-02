class SalesCollectorException(Exception): ...


class MissingEnvException(SalesCollectorException):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


class MissingSessionDataException(SalesCollectorException):
    def __init__(self) -> None:
        super().__init__(f"Missing information for the given state.")
