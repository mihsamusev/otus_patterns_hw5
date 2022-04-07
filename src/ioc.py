import threading
from dataclasses import dataclass, field
from typing import Any, Dict

from src.command import Command

default_data = {
    "ioc.register": 0,
    "scope.create": 0,
    "scope.current": 0,
    "scope.": 0,
}


@dataclass
class Scope:
    """
    Scope of the IoC container
    """

    name: str
    parent: str
    data: Dict[str, Any] = threading.local()


class IoC:
    """
    Inversion of control container
    """

    root: Scope

    @classmethod
    def resolve(cls, key: str, *args) -> Command:
        ...


if __name__ == "__main__":
    pass
