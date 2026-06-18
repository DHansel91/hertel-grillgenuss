"""Sensor platform for Hertel Grillgenuss."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import WEEKDAY_ORDER, HertelLocation
from .const import DOMAIN
from .coordinator import HertelGrillgenussCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hertel Grillgenuss sensor."""
    coordinator: HertelGrillgenussCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([HertelGrillgenussSensor(coordinator, entry)], update_before_add=True)


class HertelGrillgenussSensor(CoordinatorEntity[HertelGrillgenussCoordinator], SensorEntity):
    """
    Single sensor per config entry.

    state        → total count of matching locations
    attributes   → locations grouped & sorted by weekday,
                   plus a flat sorted list
    """

    _attr_translation_key = "standorte"

    def __init__(self, coordinator: HertelGrillgenussCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_standorte"
        self._attr_name = entry.title or "Hertel Grillgenuss Standorte"
        self._attr_native_unit_of_measurement = "Standorte"

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def native_value(self) -> int:
        """Number of locations currently found."""
        return len(self.coordinator.data) if self.coordinator.data else 0

    # ------------------------------------------------------------------
    # Attributes
    # ------------------------------------------------------------------

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data: list[HertelLocation] = self.coordinator.data or []

        # Flat list (already sorted by weekday + distance from coordinator)
        flat = [loc.as_dict() for loc in data]

        # Grouped by weekday for easy Lovelace rendering
        grouped: dict[str, list[dict[str, Any]]] = {}
        for loc in data:
            key = f"{loc.day} – {loc.day_full}"
            grouped.setdefault(key, []).append(loc.as_dict())

        return {
            # Primary: grouped by weekday (dict order = insertion = sorted)
            "by_weekday": grouped,
            # Secondary: flat sorted list
            "locations": flat,
            # Stats
            "location_count": len(data),
            # Search params for reference
            "search_latitude": self._entry.data.get("latitude"),
            "search_longitude": self._entry.data.get("longitude"),
            "search_zipcode": self._entry.data.get("zipcode", ""),
        }
