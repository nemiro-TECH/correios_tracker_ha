"""Config flow — Com suporte a Total Express e edição de apelidos."""
from __future__ import annotations
import re
import asyncio
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_KEY, CONF_DESCRIPTION, CONF_PACKAGES, CONF_SCAN_INTERVAL,
    CONF_TRACKING_CODE, DEFAULT_UPDATE_INTERVAL, DOMAIN, TRACKER_API_URL
)

# Melhoria 5: Regex atualizada para Correios e Total Express
TRACKING_REGEX = re.compile(r"^([A-Z]{2}\d{9}[A-Z]{2}|TX[A-Z0-9]+)$", re.IGNORECASE)

async def _test_api_key(api_key: str) -> str | None:
    url = TRACKER_API_URL.format(codigo="AA000000000BR")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 401:
                    return "invalid_api_key"
                return None
    except Exception:
        return "cannot_connect"

class CorreiosTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    def __init__(self):
        self._packages = []

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        errors = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            error = await _test_api_key(api_key)
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(title="Correios Tracker", data={CONF_API_KEY: api_key}, options={CONF_PACKAGES: []})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return CorreiosTrackerOptionsFlow(entry)

class CorreiosTrackerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry
        self._packages = list(entry.options.get(CONF_PACKAGES, entry.data.get(CONF_PACKAGES, [])))
        self._edit_code = None

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            action = user_input["action"]
            if action == "Adicionar": return await self.async_step_add()
            elif action == "Editar": return await self.async_step_edit() # Melhoria 2: Nova Ação
            elif action == "Remover": return await self.async_step_remove()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("action", default="Adicionar"): vol.In(["Adicionar", "Editar", "Remover"])
            }),
            description_placeholders={"summary": f"Você tem {len(self._packages)} pacote(s)."},
        )

    async def async_step_add(self, user_input: dict | None = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            code = user_input[CONF_TRACKING_CODE].strip().upper()
            if not TRACKING_REGEX.match(code):
                errors[CONF_TRACKING_CODE] = "invalid_format"
            elif any(p[CONF_TRACKING_CODE] == code for p in self._packages):
                errors[CONF_TRACKING_CODE] = "already_exists"
            else:
                self._packages.append({
                    CONF_TRACKING_CODE: code,
                    CONF_DESCRIPTION: user_input.get(CONF_DESCRIPTION) or code,
                    CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                })
                return self.async_create_entry(title="", data={CONF_PACKAGES: self._packages})

        return self.async_show_form(
            step_id="add",
            data_schema=vol.Schema({
                vol.Required(CONF_TRACKING_CODE): str,
                vol.Optional(CONF_DESCRIPTION, default=""): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=15, max=10000)),
            }), errors=errors
        )

    # Melhoria 2: Novo fluxo para Editar pacote existente
    async def async_step_edit(self, user_input: dict | None = None) -> FlowResult:
        if not self._packages:
            return self.async_abort(reason="no_packages")
            
        options = {p[CONF_TRACKING_CODE]: f"{p.get(CONF_DESCRIPTION, p[CONF_TRACKING_CODE])} ({p[CONF_TRACKING_CODE]})" for p in self._packages}
        
        if user_input is not None:
            self._edit_code = user_input["edit_code"]
            return await self.async_step_edit_form()

        return self.async_show_form(step_id="edit", data_schema=vol.Schema({vol.Required("edit_code"): vol.In(options)}))

    async def async_step_edit_form(self, user_input: dict | None = None) -> FlowResult:
        pkg = next(p for p in self._packages if p[CONF_TRACKING_CODE] == self._edit_code)
        
        if user_input is not None:
            pkg[CONF_DESCRIPTION] = user_input.get(CONF_DESCRIPTION, pkg[CONF_DESCRIPTION])
            pkg[CONF_SCAN_INTERVAL] = user_input.get(CONF_SCAN_INTERVAL, pkg.get(CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL))
            return self.async_create_entry(title="", data={CONF_PACKAGES: self._packages})

        return self.async_show_form(
            step_id="edit_form",
            data_schema=vol.Schema({
                vol.Optional(CONF_DESCRIPTION, default=pkg.get(CONF_DESCRIPTION, "")): str,
                vol.Optional(CONF_SCAN_INTERVAL, default=pkg.get(CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=15, max=10000)),
            })
        )

    async def async_step_remove(self, user_input: dict | None = None) -> FlowResult:
        if not self._packages: return self.async_abort(reason="no_packages")
        options = {p[CONF_TRACKING_CODE]: f"{p.get(CONF_DESCRIPTION, p[CONF_TRACKING_CODE])} ({p[CONF_TRACKING_CODE]})" for p in self._packages}
        if user_input is not None:
            code = user_input["remove_code"]
            self._packages = [p for p in self._packages if p[CONF_TRACKING_CODE] != code]
            return self.async_create_entry(title="", data={CONF_PACKAGES: self._packages})
        return self.async_show_form(step_id="remove", data_schema=vol.Schema({vol.Required("remove_code"): vol.In(options)}))