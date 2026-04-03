"""Inicialização da integração com atualização em tempo real (Reload sem falhas)."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
# ... (Mantenha seus outros imports: constantes, servicos, etc.)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura o Correios Tracker a partir de uma entrada de configuração."""
    hass.data.setdefault(DOMAIN, {})
    
    # ... (Seu código existente para criar os coordinators e carregar as plataformas) ...

    # Melhoria 1: Adiciona um ouvinte para que toda vez que você editar no painel, a integração se recarregue e aplique as mudanças no mesmo segundo!
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Disparado automaticamente quando um pacote é editado, adicionado ou removido pelo Menu."""
    await hass.config_entries.async_reload(entry.entry_id)

# Se você possui o serviço (Service) `update_package` para ser chamado pelo Card:
async def handle_update_package(call):
    """Serviço para atualizar o pacote e forçar o registro de dispositivos a mudar o nome instantaneamente."""
    # ... (O seu código atual para pegar os dados do call) ...
    
    # Melhoria 1 e 4: Renomeação em tempo real no banco de dados do Home Assistant (Registro de Dispositivos)
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, codigo)})
    if device:
        # Muda o nome do dispositivo instantaneamente na interface sem precisar reiniciar
        device_registry.async_update_device(
            device.id, 
            name=f"{nova_descricao} ({codigo})"
        )
    
    # Para finalizar a alteração, atualizamos o `entry` nativo (o que dispara o update_listener silenciosamente)
    hass.config_entries.async_update_entry(entry, data=novo_data, options=novos_options)