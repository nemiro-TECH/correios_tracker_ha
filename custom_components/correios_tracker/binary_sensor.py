"""Arquivo de Sensores Binários (Status de Entrega)."""
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Configura o sensor binário a partir de uma entrada de configuração."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    entities = []
    
    for coordinator in coordinators.values():
        entities.append(CorreiosDeliveredSensor(coordinator))
        
    async_add_entities(entities)

class CorreiosDeliveredSensor(CoordinatorEntity, BinarySensorEntity):
    """Sensor binário para indicar se o pacote foi entregue."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:package-variant-closed-check"

    def __init__(self, coordinator):
        """Inicializa o sensor binário."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"correios_{coordinator.tracking_code}_delivered"
        # O nome da entidade acompanhando o apelido
        self._attr_name = "Entregue" 

    @property
    def device_info(self) -> DeviceInfo:
        """Agrupa as entidades num único dispositivo com o nome 'Apelido (Código)'."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.tracking_code)},
            name=f"{self.coordinator.description} ({self.coordinator.tracking_code})",
            manufacturer="Correios / Total Express",
            model="Pacote Rastreado",
            sw_version="2.1.0",
        )

    @property
    def is_on(self) -> bool:
        """Retorna True se o pacote foi entregue."""
        if self.coordinator.data:
            return self.coordinator.data.get("is_delivered", False)
        return False