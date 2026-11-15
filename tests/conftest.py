"""A fake Flipper command line on a pseudo-terminal."""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from typing import Any

import pytest

PROMPT = b"\r\n>: "
INFO = (
    "hardware.model                : Flipper Zero\r\n"
    "hardware.uid                  : 5468726572690000\r\n"
    "hardware.name                 : Testy\r\n"
    "firmware.version              : 1.2.3\r\n"
    "firmware.origin.fork          : Momentum"
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    """Load integrations from custom_components."""


class FakeFlipper:
    """Answers the CLI: a prompt for a bare return, `info device`, `ir tx`."""

    def __init__(self) -> None:
        self.master, slave = os.openpty()
        self.port = os.ttyname(slave)
        self._slave = slave
        self.lines: list[str] = []
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        buf = b""
        while not self._stop:
            try:
                data = os.read(self.master, 65536)
            except OSError:
                return
            buf += data
            while b"\r" in buf:
                line, buf = buf.split(b"\r", 1)
                text = line.decode().strip()
                if not text:
                    os.write(self.master, PROMPT)
                    continue
                self.lines.append(text)
                reply = INFO if text == "info device" else ""
                os.write(self.master, line + b"\r\n" + reply.encode() + PROMPT)

    def close(self) -> None:
        self._stop = True
        os.close(self.master)
        os.close(self._slave)


@pytest.fixture
def fake_flipper() -> Iterator[FakeFlipper]:
    """A fake Flipper on a pty."""
    flipper = FakeFlipper()
    yield flipper
    flipper.close()
