from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vector2D:
    """
    Minimal implementation for vector for tests
    """

    x: float
    y: float

    def __add__(self, other: Vector2D):
        return Vector2D(x=self.x + other.x, y=self.y + other.y)

    def mag(self) -> float:
        """
        Vector magnitude
        """
        return math.sqrt(self.x**2 + self.y**2)
