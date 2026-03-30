"""Binary sensor entregue/em trânsito — entity_id forçado para binary_sensor.correios_*"""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_LAST_UPDATE, ATTR_TRACKING_CODE, DOMAIN
from .coordinator import CorreiosDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinators: dict[str, CorreiosDataCoordinator] = (
        hass.data[DOMAIN][entry.entry_id]["coordinators"]
    )
    async_add_entities(
        [CorreiosDeliveredSensor(coord, entry) for coord in coordinators.values()], True
    )


class CorreiosDeliveredSensor(CoordinatorEntity, BinarySensorEntity):
    """
    Binary sensor de entrega.
    ON  = Entregue ao destinatário ✅
    OFF = Em trânsito / aguardando 📦
    Estado inicial = OFF (False) enquanto não há dados.
    """

    # SEM device_class para evitar "não detectado"
    _attr_device_class = None

    def __init__(self, coordinator: CorreiosDataCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        code = coordinator.tracking_code.lower()

        self._attr_unique_id = f"correios_{code}_entregue"
        # Remover a linha self.entity_id inteiramente

    @property
    def name(self) -> str:
        desc = (self.coordinator.data or {}).get("description") or self.coordinator.tracking_code
        return f"{desc} Entregue"

    @property
    def is_on(self) -> bool:
        """Sempre retorna bool — nunca None — para evitar estado 'desconhecido'."""
        if self.coordinator.data is None:
            return False
        return bool(self.coordinator.data.get("is_delivered", False))

    @property
    def icon(self) -> str:
        return "mdi:package-check" if self.is_on else "mdi:package-variant-closed-remove"

    @property
    def extra_state_attributes(self) -> dict:
        d = self.coordinator.data or {}
        return {
            ATTR_TRACKING_CODE: d.get("tracking_code"),
            ATTR_LAST_UPDATE: d.get("last_update"),
            "status_atual": d.get("status"),
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def device_info(self) -> DeviceInfo:
        """Agrupa a entidade num dispositivo com o nome do código de rastreio."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.tracking_code)},
            name=self.coordinator.tracking_code, # O nome do device será o código
            manufacturer="Correios",
            model="Pacote Rastreado",
        )
