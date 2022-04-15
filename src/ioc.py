from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Optional


class ThreadData(threading.local):
    root_scope: Optional[Scope] = None
    current_scope: Optional[Scope] = None


@dataclass
class IoCRegisterCommand:
    key: str
    strategy: Callable

    def execute(self):
        active_scope = IoC.resolve("scopes.current")
        if self.key in active_scope.registry:
            raise KeyError(f"{self.key} already registered!")
        active_scope.registry[self.key] = self.strategy


@dataclass
class SetRootScopeCommand:
    """
    Put scope with given name as the root scope
    """

    scope_name: str

    def execute(self):
        scope = IoC.resolve("scopes.find", self.scope_name).execute()
        ThreadData.root_scope = scope
        return scope


@dataclass
class SetCurrentScopeCommand:
    """
    Put scope with given name as current scope
    """

    scope_name: str

    def execute(self):
        scope = IoC.resolve("scopes.find", self.scope_name).execute()
        ThreadData.current_scope = scope
        return scope


@dataclass
class FindScopeCommand:
    target_name: str

    def execute(self) -> Optional[Scope]:
        visit_queue = deque([ThreadData.root_scope])
        while len(visit_queue) > 0:
            scope = visit_queue.popleft()
            if scope.name == self.target_name:
                return scope
            else:
                visit_queue.extend(scope.children)

        raise ScopeNotFoundException(
            "Could not find scope {self.scope_name} from given root scope."
        )


@dataclass
class NewScopeCommand:
    """
    Append scope to the children of active_scope
    """

    parent_name: str
    scope_name: Optional[str] = None

    def execute(self) -> Scope:
        parent_scope = IoC.resolve("scopes.find", self.parent_name).execute()
        new_scope = Scope(name=self.scope_name, parent=parent_scope)
        parent_scope.children.append(new_scope)
        return new_scope


class ScopeNotFoundException(Exception):
    pass


class ScopeNotSetException(Exception):
    pass


class IoCNotFoundException(Exception):
    pass


DEFAULT_SCOPE_REGISTRY = {
    "ioc.register": lambda *args: IoCRegisterCommand(key=args[0], strategy=args[1]),
    "scopes.create": lambda *args: NewScopeCommand(*args),
    "scopes.set": lambda *args: SetCurrentScopeCommand(scope_name=args[0]),
    "scopes.find": lambda *args: FindScopeCommand(*args),
    "scopes.current": lambda *args: ThreadData.current_scope,
}


class Scope:
    """
    Scope of the IoC container
    """

    def __init__(self, name=None, parent: Optional[Scope] = None):
        self.name = name
        if self.name is None:
            self.name = str(uuid.uuid4())
        self.parent = parent
        self.children = []
        self.registry = {}
        self.__prev_scope = None

    def with_registry(self, registry: dict) -> Scope:
        """
        Builder component to initialize scope registry
        """
        self.registry = registry
        return self

    def __eq__(self, other: Scope) -> bool:
        return self.name == other.name

    def __iter__(self):
        self.__iter_out = self
        return self.__iter_out

    def __next__(self):
        if self.__iter_out is None:
            raise StopIteration
        else:
            result = self.__iter_out
            self.__iter_out = self.__iter_out.parent
            return result

    def __enter__(self):
        """
        RAII scope start
        """
        self.__prev_scope = IoC.resolve("scopes.current")
        IoC.resolve("scopes.set", self.name).execute()
        return self

    def __exit__(self, *args):
        """
        RAII scope end and resource dispose
        """
        IoC.resolve("scopes.set", self.__prev_scope.name).execute()
        self.__prev_scope = None


class IoC:
    """
    Inversion of control container with context
    polymorphism based on scopes and their local
    key / value registers
    """

    root_scope: Scope = Scope(name="root").with_registry(DEFAULT_SCOPE_REGISTRY)
    ThreadData.root_scope = root_scope
    ThreadData.current_scope = root_scope

    @classmethod
    def resolve(cls, key: str, *args: Any) -> Any:
        """
        Recursively resolve dependencies starting from the
        active scope going towards the root
        """
        if not ThreadData.current_scope:
            raise ScopeNotSetException()

        for current_scope in ThreadData.current_scope:
            resolver = current_scope.registry.get(key)
            if resolver:
                return resolver(*args)

        raise IoCNotFoundException(
            f"Could not resolve dependency {key} with args {args}"
        )


if __name__ == "__main__":
    pass
