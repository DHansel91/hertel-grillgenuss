"""Config flow for Hertel Grillgenuss integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HertelGrillgenussApiClient
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_ZIPCODE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _build_schema(
    defaults: dict[str, Any] | None = None,
    include_scan_interval: bool = False,
) -> vol.Schema:
    defaults = defaults or {}
    schema: dict[vol.Marker, Any] = {
        vol.Required(CONF_LATITUDE, default=defaults.get(CONF_LATITUDE, 49.6744)): vol.Coerce(float),
        vol.Required(CONF_LONGITUDE, default=defaults.get(CONF_LONGITUDE, 12.1489)): vol.Coerce(float),
        vol.Optional(CONF_ZIPCODE, default=defaults.get(CONF_ZIPCODE, "")): str,
    }
    if include_scan_interval:
        schema[vol.Optional(CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))] = vol.All(
            vol.Coerce(int), vol.Range(min=5, max=1440)
        )
    return vol.Schema(schema)


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> list:
    """Validate by actually fetching data."""
    session = async_get_clientsession(hass)
    client = HertelGrillgenussApiClient(
        session=session,
        latitude=data[CONF_LATITUDE],
        longitude=data[CONF_LONGITUDE],
        zipcode=data.get(CONF_ZIPCODE) or None,
    )
    return await client.async_get_locations()


class HertelGrillgenussConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hertel Grillgenuss."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Clean up optional zipcode
            if not user_input.get(CONF_ZIPCODE):
                user_input.pop(CONF_ZIPCODE, None)

            try:
                await _validate_input(self.hass, user_input)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during config flow validation")
                errors["base"] = "unknown"
            else:
                title = f"Hertel Grillgenuss ({user_input[CONF_LATITUDE]:.4f}, {user_input[CONF_LONGITUDE]:.4f})"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> HertelGrillgenussOptionsFlow:
        """Return the options flow."""
        return HertelGrillgenussOptionsFlow()


class HertelGrillgenussOptionsFlow(OptionsFlow):
    """Handle options for Hertel Grillgenuss."""

    # KEIN __init__ mit config_entry – HA 2024.x stellt self.config_entry automatisch bereit.

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            if not user_input.get(CONF_ZIPCODE):
                user_input.pop(CONF_ZIPCODE, None)
            try:
                await _validate_input(self.hass, {**current, **user_input})
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(
                defaults={**current, **(user_input or {})},
                include_scan_interval=True,
            ),
            errors=errors,
        )
