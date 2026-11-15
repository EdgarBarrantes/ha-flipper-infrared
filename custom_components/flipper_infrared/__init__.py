"""Flipper Zero as an infrared emitter for Home Assistant, over USB."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .flipper import Flipper, FlipperError

PLATFORMS = [Platform.INFRARED]


@dataclass
class FlipperData:
    """The port, what the Flipper says about itself, and a lock: one CLI session at a time."""

    port: str
    info: dict[str, str]
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


type FlipperConfigEntry = ConfigEntry[FlipperData]


def _probe(port: str) -> dict[str, str]:
    with Flipper(port) as flipper:
        return flipper.device_info()


async def async_setup_entry(hass: HomeAssistant, entry: FlipperConfigEntry) -> bool:
    """Check the Flipper answers, then add its emitter."""
    port = entry.data[CONF_PORT]
    try:
        info = await hass.async_add_executor_job(_probe, port)
    except FlipperError as err:
        raise ConfigEntryNotReady(str(err)) from err
    entry.runtime_data = FlipperData(port=port, info=info)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FlipperConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
