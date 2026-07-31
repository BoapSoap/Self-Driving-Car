"""Elapsed-time based asymmetric command ramps."""

from __future__ import annotations


def move_toward(current: float, target: float, max_delta: float) -> float:
    if max_delta < 0:
        raise ValueError("max_delta cannot be negative")
    if current < target:
        return min(target, current + max_delta)
    return max(target, current - max_delta)


class ThrottleLimiter:
    def __init__(self, acceleration_per_s: float, deceleration_per_s: float):
        self.acceleration_per_s = acceleration_per_s
        self.deceleration_per_s = deceleration_per_s
        self.value = 0.0

    def update(self, target: float, elapsed_s: float) -> float:
        target = max(0.0, min(1.0, target))
        rate = self.acceleration_per_s if target > self.value else self.deceleration_per_s
        self.value = move_toward(self.value, target, rate * max(0.0, elapsed_s))
        return self.value

    def stop(self) -> None:
        self.value = 0.0


class SteeringLimiter:
    def __init__(self, outward_per_s: float, recenter_per_s: float):
        self.outward_per_s = outward_per_s
        self.recenter_per_s = recenter_per_s
        self.value = 0.0

    def update(self, target: float, elapsed_s: float) -> float:
        target = max(-1.0, min(1.0, target))
        moving_toward_center = abs(target) < abs(self.value) or target == 0
        rate = self.recenter_per_s if moving_toward_center else self.outward_per_s
        self.value = move_toward(self.value, target, rate * max(0.0, elapsed_s))
        return self.value

    def center(self) -> None:
        self.value = 0.0
