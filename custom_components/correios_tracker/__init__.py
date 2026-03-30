"""Correios Tracker — hub único, serviços persistentes."""
from __future__ import annotations

import logging
import re

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_API_KEY,
    CONF_DESCRIPTION,
    CONF_PACKAGES,
    CONF_SCAN_INTERVAL,
    CONF_TRACKING_CODE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import CorreiosDataCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
TRACKING_REGEX = re.compile(r"^[A-Z]{2}\d{9}[A-Z]{2}$")

ADD_PACKAGE_SCHEMA = vol.Schema({
    vol.Required(CONF_TRACKING_CODE): cv.string,
    vol.Optional(CONF_DESCRIPTION, default=""): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
        vol.Coerce(int), vol.Range(min=15, max=1440)
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

    # ── add_package: cadastra novo OU atualiza descrição/intervalo se já existir ──
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
            # ── ATUALIZA descrição e intervalo do pacote existente ──
            existing[CONF_DESCRIPTION] = new_desc
            existing[CONF_SCAN_INTERVAL] = new_interval
            hass.config_entries.async_update_entry(entry, options={CONF_PACKAGES: packages})

            # Atualiza o coordinator em memória sem recriar
            if entry.entry_id in hass.data.get(DOMAIN, {}):
                coordinators: dict = hass.data[DOMAIN][entry.entry_id]["coordinators"]
                if code in coordinators:
                    # Atualiza a descrição e o intervalo na memória
                    coordinators[code].description = new_desc
                    from datetime import timedelta
                    coordinators[code].update_interval = timedelta(minutes=new_interval)
                    # Força o HA a reconhecer o novo nome
                    if coordinators[code].data:
                        coordinators[code].data["description"] = new_desc
                        coordinators[code].async_set_updated_data(coordinators[code].data)

            _LOGGER.info("Pacote %s atualizado: desc=%s interval=%s", code, new_desc, new_interval)
        else:
            # ── ADICIONA novo pacote ──
            new_pkg = {
                CONF_TRACKING_CODE: code,
                CONF_DESCRIPTION: new_desc,
                CONF_SCAN_INTERVAL: new_interval,
            }
            packages.append(new_pkg)
            hass.config_entries.async_update_entry(entry, options={CONF_PACKAGES: packages})

            if entry.entry_id in hass.data.get(DOMAIN, {}):
                await _setup_coordinator(hass, entry, new_pkg, from_service=True)

            _LOGGER.info("Pacote %s adicionado", code)

    # ── remove_package: remove pacote e entidades ──
    async def handle_remove_package(call: ServiceCall) -> None:
        entry = _get_entry(hass)
        if not entry:
            _LOGGER.error("Correios Tracker não está configurado")
            return

        code = call.data[CONF_TRACKING_CODE].upper().strip()

        # 1. Remove entidades do registry PRIMEIRO — antes do reload disparado pelo update_entry
        registry = er.async_get(hass)
        for entity_entry in list(er.async_entries_for_config_entry(registry, entry.entry_id)):
            if f"correios_{code.lower()}" in entity_entry.unique_id:
                registry.async_remove(entity_entry.entity_id)
                _LOGGER.debug("Entidade %s removida", entity_entry.entity_id)

        # 2. Remove coordinator da memória
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            hass.data[DOMAIN][entry.entry_id]["coordinators"].pop(code, None)

        # 3. Atualiza options (dispara reload — package já não está na lista)
        packages: list[dict] = list(entry.options.get(CONF_PACKAGES, []))
        packages = [p for p in packages if p[CONF_TRACKING_CODE] != code]
        hass.config_entries.async_update_entry(entry, options={CONF_PACKAGES: packages})

        _LOGGER.info("Pacote %s removido", code)

    hass.services.async_register(DOMAIN, "add_package", handle_add_package, schema=ADD_PACKAGE_SCHEMA)
    hass.services.async_register(DOMAIN, "remove_package", handle_remove_package, schema=REMOVE_PACKAGE_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api_key = entry.data[CONF_API_KEY]
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {"api_key": api_key, "coordinators": {}}

    for pkg in entry.options.get(CONF_PACKAGES, []):
        await _setup_coordinator(hass, entry, pkg, from_service=False)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _setup_coordinator(
    hass: HomeAssistant, entry: ConfigEntry, pkg: dict, from_service: bool = False
) -> CorreiosDataCoordinator:
    api_key: str = hass.data[DOMAIN][entry.entry_id]["api_key"]
    coordinators: dict = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    code = pkg[CONF_TRACKING_CODE]

    if code in coordinators:
        return coordinators[code]

    coordinator = CorreiosDataCoordinator(
        hass,
        tracking_code=code,
        description=pkg.get(CONF_DESCRIPTION, code),
        api_key=api_key,
        scan_interval=pkg.get(CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL),
    )

    if from_service:
        await coordinator.async_refresh()
    else:
        await coordinator.async_config_entry_first_refresh()

    coordinators[code] = coordinator
    return coordinator


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
