"""Correios Tracker — inicialização com serviços e reload automático."""
from __future__ import annotations

import logging
import re

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_API_KEY, CONF_DESCRIPTION, CONF_PACKAGES,
    CONF_SCAN_INTERVAL, CONF_TRACKING_CODE,
    DEFAULT_UPDATE_INTERVAL, DOMAIN,
)
from .coordinator import CorreiosDataCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Aceita Correios (AA123456789BR) e Total Express (TX...)
TRACKING_REGEX = re.compile(r"^([A-Z]{2}\d{9}[A-Z]{2}|TX[A-Z0-9]+)$", re.IGNORECASE)

# Impede configuração via configuration.yaml (apenas via UI)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

ADD_PACKAGE_SCHEMA = vol.Schema({
    vol.Required(CONF_TRACKING_CODE): cv.string,
    vol.Optional(CONF_DESCRIPTION, default=""): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
        vol.Coerce(int), vol.Range(min=15, max=10000)
    ),
})

REMOVE_PACKAGE_SCHEMA = vol.Schema({
    vol.Required(CONF_TRACKING_CODE): cv.string,
})


def _get_entry(hass: HomeAssistant) -> ConfigEntry | None:
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Registra serviços UMA VEZ — sobrevivem a reloads do config entry."""
    hass.data.setdefault(DOMAIN, {})

    async def handle_add_package(call: ServiceCall) -> None:
        entry = _get_entry(hass)
        if not entry:
            _LOGGER.error("Correios Tracker não está configurado")
            return

        code = call.data[CONF_TRACKING_CODE].upper().strip()
        if not TRACKING_REGEX.match(code):
            _LOGGER.error("Código inválido: %s", code)
            return

        new_desc     = call.data.get(CONF_DESCRIPTION, "").strip() or code
        new_interval = call.data.get(CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL)

        packages: list[dict] = list(entry.options.get(CONF_PACKAGES, []))
        existing = next((p for p in packages if p[CONF_TRACKING_CODE] == code), None)

        if existing:
            # Atualiza apelido e intervalo
            existing[CONF_DESCRIPTION] = new_desc
            existing[CONF_SCAN_INTERVAL] = new_interval
            hass.config_entries.async_update_entry(entry, options={CONF_PACKAGES: packages})

            if entry.entry_id in hass.data.get(DOMAIN, {}):
                coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
                if code in coordinators:
                    from datetime import timedelta
                    coordinators[code].description = new_desc
                    coordinators[code].update_interval = timedelta(minutes=new_interval)
                    if coordinators[code].data:
                        coordinators[code].data["description"] = new_desc
                        coordinators[code].async_set_updated_data(coordinators[code].data)

            # Atualiza nome no device registry
            device_registry = dr.async_get(hass)
            device = device_registry.async_get_device(identifiers={(DOMAIN, code)})
            if device:
                device_registry.async_update_device(
                    device.id, name=f"{new_desc} ({code})"
                )
            _LOGGER.info("Pacote %s atualizado", code)
        else:
            new_pkg = {
                CONF_TRACKING_CODE: code,
                CONF_DESCRIPTION: new_desc,
                CONF_SCAN_INTERVAL: new_interval,
            }
            packages.append(new_pkg)
            hass.config_entries.async_update_entry(entry, options={CONF_PACKAGES: packages})

            if entry.entry_id in hass.data.get(DOMAIN, {}):
                api_key = hass.data[DOMAIN][entry.entry_id]["api_key"]
                coordinator = CorreiosDataCoordinator(
                    hass,
                    tracking_code=code,
                    description=new_desc,
                    api_key=api_key,
                    scan_interval=new_interval,
                )
                await coordinator.async_refresh()
                hass.data[DOMAIN][entry.entry_id]["coordinators"][code] = coordinator
            _LOGGER.info("Pacote %s adicionado", code)

    async def handle_remove_package(call: ServiceCall) -> None:
        entry = _get_entry(hass)
        if not entry:
            _LOGGER.error("Correios Tracker não está configurado")
            return

        code = call.data[CONF_TRACKING_CODE].upper().strip()

        # 1. Remove entidades do registry PRIMEIRO
        registry = er.async_get(hass)
        for entity_entry in list(er.async_entries_for_config_entry(registry, entry.entry_id)):
            if f"correios_{code.lower()}" in entity_entry.unique_id:
                registry.async_remove(entity_entry.entity_id)

        # 2. Remove coordinator
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            hass.data[DOMAIN][entry.entry_id]["coordinators"].pop(code, None)

        # 3. Atualiza options (dispara reload)
        packages: list[dict] = list(entry.options.get(CONF_PACKAGES, []))
        packages = [p for p in packages if p[CONF_TRACKING_CODE] != code]
        hass.config_entries.async_update_entry(entry, options={CONF_PACKAGES: packages})

        _LOGGER.info("Pacote %s removido", code)

    hass.services.async_register(DOMAIN, "add_package",    handle_add_package,    schema=ADD_PACKAGE_SCHEMA)
    hass.services.async_register(DOMAIN, "remove_package", handle_remove_package, schema=REMOVE_PACKAGE_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configura coordinators para todos os pacotes e carrega as plataformas."""
    api_key = entry.data.get(CONF_API_KEY)
    hass.data.setdefault(DOMAIN, {})

    coordinators = {}
    # Lê de options (padrão), fallback para data (instalações antigas)
    packages = entry.options.get(CONF_PACKAGES, entry.data.get(CONF_PACKAGES, []))

    for pkg in packages:
        code = pkg[CONF_TRACKING_CODE]
        coordinator = CorreiosDataCoordinator(
            hass,
            tracking_code=code,
            description=pkg.get(CONF_DESCRIPTION, code),
            api_key=api_key,
            scan_interval=pkg.get(CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators[code] = coordinator

    # Guarda api_key E coordinators — ambos usados pelos serviços
    hass.data[DOMAIN][entry.entry_id] = {
        "api_key": api_key,
        "coordinators": coordinators,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recarrega a integração quando as options são alteradas pelo menu."""
    _LOGGER.info("Opções atualizadas. Recarregando Correios Tracker...")
    await hass.config_entries.async_reload(entry.entry_id)
