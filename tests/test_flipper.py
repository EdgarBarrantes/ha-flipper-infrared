"""The CLI client against a fake Flipper, and the emitter in Home Assistant."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.components.infrared import async_send_command
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from infrared_protocols.commands.nec import NECCommand

from custom_components.flipper_infrared.const import DOMAIN
from custom_components.flipper_infrared.flipper import Flipper, FlipperError, ir_tx_line, send


def test_ir_tx_line() -> None:
    assert ir_tx_line([9000, -4500, 560, -560, 560], 38000) == "ir tx RAW F:38000 DC:33 9000 4500 560 560 560"
    # leading space dropped, repeated signs merged, zeros skipped
    assert ir_tx_line([-100, 500, 0, -200, -300, 400], 36000) == "ir tx RAW F:36000 DC:33 500 500 400"
    with pytest.raises(FlipperError):
        ir_tx_line([-5], 38000)


def test_cli(fake_flipper) -> None:
    with Flipper(fake_flipper.port) as flipper:
        info = flipper.device_info()
    assert info["hardware.name"] == "Testy"
    assert info["hardware.uid"] == "5468726572690000"
    send(fake_flipper.port, [6000, -3000, 660], 38000)
    assert fake_flipper.lines[-1] == "ir tx RAW F:38000 DC:33 6000 3000 660"


def test_no_port() -> None:
    with pytest.raises(FlipperError):
        Flipper("/dev/does-not-exist")


async def test_flow_and_emitter(hass: HomeAssistant, fake_flipper) -> None:
    with patch("custom_components.flipper_infrared.config_flow._ports", return_value=[fake_flipper.port]):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PORT: fake_flipper.port})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Flipper Testy"
    assert result["result"].unique_id == "5468726572690000"
    await hass.async_block_till_done()

    entity_id = "infrared.testy"
    assert hass.states.get(entity_id) is not None
    await async_send_command(hass, entity_id, NECCommand(address=0x04, command=0x08))
    assert fake_flipper.lines[-1].startswith("ir tx RAW F:38000 DC:33 9000 4500")
    assert hass.states.get(entity_id).state not in (None, "unknown")


async def test_flow_cannot_connect(hass: HomeAssistant) -> None:
    with patch("custom_components.flipper_infrared.config_flow._ports", return_value=[]):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PORT: "/dev/nothing"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
