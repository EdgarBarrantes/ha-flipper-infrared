"""Config flow: pick the Flipper's serial port."""

from __future__ import annotations

import os
from typing import Any

import probatio
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PORT
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import BY_ID, DOMAIN
from .flipper import Flipper, FlipperError


def _ports() -> list[str]:
    """Flippers first, by their stable /dev/serial/by-id names."""
    try:
        names = sorted(os.listdir(BY_ID))
    except OSError:
        names = []
    ports = [os.path.join(BY_ID, n) for n in names]
    return sorted(ports, key=lambda p: "Flipper" not in p)


def _probe(port: str) -> dict[str, str]:
    with Flipper(port) as flipper:
        return flipper.device_info()


class FlipperInfraredConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a Flipper Zero connected by USB."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose the port and check a Flipper answers on it."""
        errors: dict[str, str] = {}
        if user_input is not None:
            port = user_input[CONF_PORT]
            try:
                info = await self.hass.async_add_executor_job(_probe, port)
            except FlipperError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info.get("hardware.uid") or port)
                self._abort_if_unique_id_configured(updates={CONF_PORT: port})
                name = info.get("hardware.name")
                return self.async_create_entry(
                    title=f"Flipper {name}" if name else "Flipper Zero", data={CONF_PORT: port}
                )
        ports = await self.hass.async_add_executor_job(_ports)
        schema = probatio.Schema(
            {
                probatio.Required(CONF_PORT, default=ports[0] if ports else "/dev/ttyACM0"): SelectSelector(
                    SelectSelectorConfig(options=ports, custom_value=True, mode=SelectSelectorMode.DROPDOWN)
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
