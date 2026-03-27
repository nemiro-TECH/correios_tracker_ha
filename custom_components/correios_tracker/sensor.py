"""Sensor de status dos Correios."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_DESCRIPTION, ATTR_EVENTS, ATTR_LAST_UPDATE, ATTR_LOCATION, ATTR_TRACKING_CODE, DOMAIN
from .coordinator import CorreiosDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinators: dict[str, CorreiosDataCoordinator] = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    async_add_entities([CorreiosStatusSensor(coord, entry) for coord in coordinators.values()], True)


class CorreiosStatusSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator: CorreiosDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        code = coordinator.tracking_code.lower()
        self._attr_unique_id = f"correios_{code}_status"
        self.entity_id = f"sensor.correios_{code}_status"
        self._attr_icon = "mdi:package-variant-closed"

    @property
    def name(self) -> str:
        d = self.coordinator.data or {}
        return f"{d.get('description') or self.coordinator.tracking_code} Status"

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data or {}).get("status")

    @property
    def extra_state_attributes(self) -> dict:
        d = self.coordinator.data or {}
        return {
            ATTR_TRACKING_CODE: d.get("tracking_code"),
            ATTR_DESCRIPTION: d.get("description"),
            ATTR_LOCATION: d.get("location"),
            "localizacao_detalhada": d.get("location_raw"),
            ATTR_LAST_UPDATE: d.get("last_update"),
            ATTR_EVENTS: d.get("events", []),
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success
