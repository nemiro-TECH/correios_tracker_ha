"""Arquivo de Sensores. Adicionando Dispositivos (Devices) unificados."""
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

class CorreiosSensor(SensorEntity):
    """Sensor do pacote."""

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = f"correios_{coordinator.tracking_code}_status"
        # O nome da Entidade acompanhará o apelido dinâmico do coordinator
        self._attr_name = f"{coordinator.description} Status" 

    # Melhoria 4: Propriedade Device Info (Adicione isto a todos os sensores e sensores binários da integração)
    @property
    def device_info(self) -> DeviceInfo:
        """Informa ao Home Assistant para agrupar todas as entidades com este tracking_code em um único Dispositivo."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.tracking_code)},
            name=f"{self.coordinator.description} ({self.coordinator.tracking_code})",
            manufacturer="Correios / Total Express",
            model="Pacote Rastreado",
            sw_version="2.1.0"
        )
        
    @property
    def state(self):
        return self.coordinator.data.get("status")