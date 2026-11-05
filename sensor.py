"""Arquivo de Sensores. Adicionando Dispositivos (Devices) unificados."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Configura o sensor a partir de uma entrada de configuração."""
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    entities = []
    
    for coordinator in coordinators.values():
        entities.append(CorreiosSensor(coordinator))
        
    async_add_entities(entities)

class CorreiosSensor(CoordinatorEntity, SensorEntity):
    """Sensor principal do pacote que indica o estado atual da entrega."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:package-variant"

    def __init__(self, coordinator):
        """Inicializa o sensor e associa ao coordenador."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"correios_{coordinator.tracking_code}_status"
        # O nome da Entidade acompanhará o apelido dinâmico do coordinator
        self._attr_name = "Status"

    @property
    def device_info(self) -> DeviceInfo:
        """Agrupa este sensor e o sensor binário num único Dispositivo."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.tracking_code)},
            name=f"{self.coordinator.description} ({self.coordinator.tracking_code})",
            manufacturer="Correios / Total Express",
            model="Pacote Rastreado",
            sw_version="0.1.2"
        )
        
    @property
    def native_value(self):
        """Devolve o status (estado) mais recente."""
        if self.coordinator.data:
            return self.coordinator.data.get("status", "Desconhecido")
        return "Aguardando atualização"
        
    @property
    def extra_state_attributes(self):
        """Devolve os atributos (localização, data, histórico)."""
        if self.coordinator.data:
            return {
                "codigo_objeto": self.coordinator.tracking_code,
                "descricao": self.coordinator.description,
                "ultima_atualizacao": self.coordinator.data.get("last_update"),
                "localizacao": self.coordinator.data.get("location"),
                "movimentacoes": self.coordinator.data.get("events", [])
            }
        return {}