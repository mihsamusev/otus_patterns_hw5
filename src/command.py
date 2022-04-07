import math
from dataclasses import dataclass, field
from typing import Protocol, Sequence

from src.core import Vector2D


class Command(Protocol):
    def execute(self):
        """
        Execute command
        """


class CommandException(Exception):
    """
    Exception thrown on Command.execute() failure
    """


class UsesFuel(Protocol):
    """
    Interface for classes that are capable of burning fuel
    """

    @property
    def fuel(self) -> int:
        ...

    @fuel.setter
    def fuel(self) -> int:
        ...

    @property
    def burn_rate(self) -> int:
        ...


class CanMove(Protocol):
    """
    Interface for classes that are capable of linear movement
    """

    @property
    def position(self) -> Vector2D:
        ...

    @position.setter
    def position(self, value: Vector2D):
        ...

    @property
    def velocity(self) -> Vector2D:
        ...


class CanTurn(Protocol):
    """
    Interface for classes that are capable of turning
    """

    @property
    def direction(self) -> int:
        ...

    @direction.setter
    def direction(self, value: int):
        ...

    @property
    def max_directions(self) -> int:
        ...

    @property
    def angular_velocity(self) -> int:
        ...


class CanRedirectVelocity(Protocol):
    """
    Interface for classes that are capable changing velocity
    according to direction
    """

    @property
    def direction(self) -> int:
        ...

    @property
    def max_directions(self) -> int:
        ...

    @property
    def velocity(self) -> Vector2D:
        ...

    @velocity.setter
    def velocity(self, value: Vector2D):
        ...


class CanMoveWithFuel(CanMove, UsesFuel):  # type: ignore
    """
    Union of CanMove and UsesFuel interfaces for objects
    that can move and have fuel
    """

    pass


class CanTurnWithVelocity(CanTurn, CanRedirectVelocity):  # type: ignore
    """
    Union of CanTurn and CanRedirectVelocity interfaces for
    objects that turn and have velocity
    """

    pass


@dataclass(frozen=True)
class MoveCommand:
    """
    Executes linear movement of an object implementing CanMove
    """

    body: CanMove

    def execute(self):
        self.body.position += self.body.velocity


@dataclass(frozen=True)
class CheckFuelCommand:
    body: UsesFuel

    def execute(self):
        if self.body.fuel < self.body.burn_rate:
            raise CommandException


@dataclass(frozen=True)
class BurnFuelCommand:
    body: UsesFuel

    def execute(self):
        self.body.fuel -= self.body.burn_rate


@dataclass(frozen=True)
class MacroCommand:
    commands: Sequence[Command] = field(default_factory=list)

    def execute(self):
        for command in self.commands:
            try:
                command.execute()
            except Exception as e:
                raise CommandException(e)


@dataclass(frozen=True)
class TurnCommand:
    body: CanTurn

    def execute(self):
        self.body.direction = (
            self.body.direction + self.body.angular_velocity
        ) % self.body.max_directions


@dataclass(frozen=True)
class RedirectVelocityCommand:
    body: CanRedirectVelocity

    def execute(self):
        magnitude = self.body.velocity.mag()
        if math.isclose(magnitude, 0):
            return

        angle = 2 * math.pi * self.body.direction / self.body.max_directions
        vx = magnitude * math.cos(angle)
        vy = magnitude * math.sin(angle)
        self.body.velocity = Vector2D(vx, vy)
