"""The Flipper's infrared LED as an emitter entity."""

from __future__ import annotations

from homeassistant.components.infrared import InfraredCommand, InfraredEmitterEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import FlipperConfigEntry
from .const import DOMAIN
from .flipper import FlipperError, send

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FlipperConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the emitter."""
    async_add_entities([FlipperEmitter(entry)])


class FlipperEmitter(InfraredEmitterEntity):
    """Sends raw timings with `ir tx RAW` on the Flipper's command line."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: FlipperConfigEntry) -> None:
        """Initialize the emitter."""
        self._data = entry.runtime_data
        info = self._data.info
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=info.get("hardware.name") or entry.title,
            manufacturer="Flipper Devices",
            model="Flipper Zero",
            sw_version=" ".join(
                v for v in (info.get("firmware.origin.fork"), info.get("firmware.version")) if v
            )
            or None,
        )

    async def async_send_command(self, command: InfraredCommand) -> None:
        """Send the command's timings."""
        timings = command.get_raw_timings()
        frequency = command.modulation or 38000
        async with self._data.lock:
            try:
                await self.hass.async_add_executor_job(send, self._data.port, timings, frequency)
            except FlipperError as err:
                raise HomeAssistantError(f"Flipper: {err}") from err
        if command.repeat_count:
            for _ in range(command.repeat_count):
                async with self._data.lock:
                    await self.hass.async_add_executor_job(send, self._data.port, timings, frequency)
