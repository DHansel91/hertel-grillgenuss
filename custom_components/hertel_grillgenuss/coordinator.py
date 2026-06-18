"""DataUpdateCoordinator for Hertel Grillgenuss."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HertelGrillgenussApiClient, HertelLocation
from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_SCAN_INTERVAL,
    CONF_ZIPCODE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class HertelGrillgenussCoordinator(DataUpdateCoordinator[list[HertelLocation]]):
    """Coordinator to fetch Hertel Grillgenuss data periodically."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self._entry = entry
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval),
        )

        session = async_get_clientsession(hass)
        self._client = HertelGrillgenussApiClient(
            session=session,
            latitude=entry.data[CONF_LATITUDE],
            longitude=entry.data[CONF_LONGITUDE],
            zipcode=entry.data.get(CONF_ZIPCODE),
        )

    async def _async_update_data(self) -> list[HertelLocation]:
        """Fetch data from the Hertel Grillgenuss website."""
        try:
            locations = await self._client.async_get_locations()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with Hertel Grillgenuss: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Unexpected error fetching Hertel locations: {err}") from err

        return locations
