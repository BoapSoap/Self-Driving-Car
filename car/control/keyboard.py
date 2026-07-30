"""Nonblocking terminal input isolated behind an input-provider interface.

SSH terminals normally report key presses and repeat events, not key releases.
Keys are therefore inferred as held only until ``key_expiry_s`` after the most
recent event. A true game-controller provider can replace this module later.
"""

from __future__ import annotations

import os
import select
import sys
import time
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class KeyState:
    w: bool = False
    a: bool = False
    s: bool = False
    d: bool = False
    emergency_stop: bool = False
    quit: bool = False
    had_input: bool = False


class InputProvider(Protocol):
    def poll(self) -> KeyState: ...
    def close(self) -> None: ...


class TerminalKeyboard:
    def __init__(self, key_expiry_s: float = 0.18):
        self.key_expiry_s = key_expiry_s
        self._last: dict[str, float] = {}
        self._windows = os.name == "nt"
        self._old_termios = None

    def __enter__(self) -> "TerminalKeyboard":
        if not self._windows:
            if not sys.stdin.isatty():
                raise RuntimeError("keyboard control requires an interactive TTY")
            import termios
            import tty

            self._old_termios = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        return self

    def poll(self) -> KeyState:
        now = time.monotonic()
        chars: list[str] = []
        if self._windows:
            import msvcrt

            while msvcrt.kbhit():
                chars.append(msvcrt.getwch())
        else:
            while select.select([sys.stdin], [], [], 0)[0]:
                chars.append(sys.stdin.read(1))
        result = KeyState()
        for char in chars:
            key = char.lower()
            if key in "wasd":
                self._last[key] = now
                result.had_input = True
            elif key == " ":
                result.emergency_stop = True
                result.had_input = True
            elif key == "q":
                result.quit = True
                result.had_input = True
        for key in "wasd":
            setattr(result, key, now - self._last.get(key, float("-inf")) <= self.key_expiry_s)
        return result

    def close(self) -> None:
        if self._old_termios is not None:
            import termios

            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_termios)
            self._old_termios = None

    def __exit__(self, *_: object) -> None:
        self.close()
