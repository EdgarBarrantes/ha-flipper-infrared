"""A Flipper Zero's command line over USB serial (Linux), enough to send infrared."""

from __future__ import annotations

import os
import select
import termios
import time
from typing import Self

PROMPT = b"\r\n>: "


class FlipperError(Exception):
    """The Flipper didn't answer or refused a command."""


class Flipper:
    """One CLI session: opened, used, closed (the port isn't held between commands)."""

    def __init__(self, port: str, timeout: float = 3) -> None:
        """Open the port and wait for the prompt."""
        try:
            self.fd: int | None = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        except OSError as err:
            raise FlipperError(f"can't open {port}: {err}") from err
        try:
            attrs = termios.tcgetattr(self.fd)
            attrs[0] = attrs[1] = attrs[3] = 0
            attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
            termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
            termios.tcflush(self.fd, termios.TCIOFLUSH)
            self._write(b"\r")
            if PROMPT not in self._read_until(PROMPT, timeout):
                raise FlipperError(f"no CLI prompt on {port} (is an app or qFlipper using it?)")
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        """Close the port."""
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self) -> Self:
        """Use as a context manager."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Close on exit."""
        self.close()

    def _read_until(self, token: bytes, timeout: float) -> bytes:
        assert self.fd is not None
        out, end = b"", time.monotonic() + timeout
        while time.monotonic() < end and token not in out:
            ready, _, _ = select.select([self.fd], [], [], 0.2)
            if ready:
                try:
                    out += os.read(self.fd, 65536)
                except BlockingIOError:  # another reader took it first
                    continue
        return out

    def _write(self, data: bytes) -> None:
        assert self.fd is not None
        view = memoryview(data)
        end = time.monotonic() + 10
        while view:
            if time.monotonic() > end:
                raise FlipperError("write timed out")
            select.select([], [self.fd], [], 1)
            try:
                n = os.write(self.fd, view)
            except BlockingIOError:
                continue
            view = view[n:]

    def command(self, line: str, timeout: float = 15) -> str:
        """Run a CLI command, return its output."""
        self._write(line.encode() + b"\r")
        out = self._read_until(PROMPT, timeout)
        if PROMPT not in out:
            raise FlipperError(f"no answer to {line.split(' ', 2)[:2]}")
        body = out.split(b"\r\n", 1)[1] if b"\r\n" in out else out
        return body.replace(PROMPT, b"").decode(errors="replace").strip()

    def device_info(self) -> dict[str, str]:
        """Name, firmware and hardware details from `info device`."""
        info: dict[str, str] = {}
        for line in self.command("info device", timeout=5).splitlines():
            key, sep, value = line.partition(":")
            if sep:
                info[key.strip()] = value.strip()
        return info


def ir_tx_line(timings: list[int], frequency: int, duty: int = 33) -> str:
    """The CLI line sending raw timings (positive marks, negative spaces).

    The Flipper takes alternating durations starting with a mark: two marks or two spaces in a
    row are merged, and leading spaces dropped.
    """
    merged: list[int] = []
    for t in timings:
        if t == 0 or (not merged and t < 0):
            continue
        if merged and (merged[-1] > 0) == (t > 0):
            merged[-1] += t
        else:
            merged.append(t)
    if not merged:
        raise FlipperError("nothing to send")
    return f"ir tx RAW F:{frequency} DC:{duty} " + " ".join(str(abs(t)) for t in merged)


def send(port: str, timings: list[int], frequency: int) -> None:
    """Send raw infrared timings."""
    with Flipper(port) as flipper:
        out = flipper.command(ir_tx_line(timings, frequency))
    if out and ("rror" in out or "Usage" in out):
        raise FlipperError(out.splitlines()[0])
