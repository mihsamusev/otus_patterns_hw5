from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class ThreadData(threading.local):
    root_scope: Optional[Scope] = None
    current_scope: Optional[Scope] = None


@dataclass
class IoCRegisterCommand:
    """
    Registers a strategy for resolving a specific key with IoC
    """

    key: str
    strategy: Callable

    def execute(self):
        active_scope = ThreadData.current_scope
        if self.key in active_scope.registry:
            raise KeyError(f"{self.key} already registered!")
        active_scope.registry[self.key] = self.strategy


@dataclass
class FindScopeCommand:
    """
    Breadth first search through through root_scope tree
    """

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
class SetCurrentScopeCommand:
    """
    Put scope with given name as current scope
    """

    scope_name: str

    def execute(self):
        scope = FindScopeCommand(self.scope_name).execute()
        ThreadData.current_scope = scope
        return scope


@dataclass
class NewScopeCommand:
    """
    Append scope to the children of active_scope
    """

    parent_name: str
    scope_name: Optional[str] = None

    def __post_init__(self):
        if not self.scope_name:
            self.scope_name = str(uuid.uuid4())

    def execute(self) -> Scope:
        parent_scope = FindScopeCommand(self.parent_name).execute()
        new_scope = Scope(
            name=self.scope_name,
            parent=parent_scope,
            setter_scope=ThreadData.current_scope,
        )
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


@dataclass
class Scope:
    """
    Scope of the IoC container
    """

    name: str
    parent: Optional[Scope] = None
    setter_scope: Optional[Scope] = None
    children: List[Scope] = field(default_factory=list)
    registry: Dict[str, Callable] = field(default_factory=dict)

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
        """
        Iterate from leaf to root
        """
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
        current = ThreadData.current_scope
        if self != current:
            self.setter_scope = current
            SetCurrentScopeCommand(self.name).execute()
            # IoC.resolve("scopes.set", self.name).execute()
        return self

    def __exit__(self, *args):
        """
        RAII scope end and resource dispose
        """
        SetCurrentScopeCommand(self.setter_scope.name).execute()
        # IoC.resolve("scopes.set", self.setter_scope.name).execute()


class IoC:
    """
    Inversion of control container with context
    polymorphism based on scopes and their local
    key / value registers
    """

    def __init__(self):
        ...
        root_scope: Scope = Scope(name="root").with_registry(DEFAULT_SCOPE_REGISTRY)
        ThreadData.root_scope = root_scope
        ThreadData.current_scope = root_scope

    def resolve(self, key: str, *args: Any) -> Any:
        """
        Resolve dependencies starting from the
        active scope going towards the root scope
        """
        if not ThreadData.current_scope:
            raise ScopeNotSetException()

        for scope in ThreadData.current_scope:
            resolver = scope.registry.get(key)
            if resolver:
                return resolver(*args)

        raise IoCNotFoundException(
            f"Could not resolve dependency {key} with args {args}"
        )


if __name__ == "__main__":
    pass
