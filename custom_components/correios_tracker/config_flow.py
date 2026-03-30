"""Config flow — valida API key antes de aceitar."""
from __future__ import annotations

import re
import asyncio
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_KEY,
    CONF_DESCRIPTION,
    CONF_PACKAGES,
    CONF_SCAN_INTERVAL,
    CONF_TRACKING_CODE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    TRACKER_API_URL,
)

TRACKING_REGEX = re.compile(r"^[A-Z]{2}\d{9}[A-Z]{2}$")

async def _test_api_key(api_user: str, api_token: str) -> str | None:
    """Testa o utilizador e token da API Link&Track."""
    # Se usar o usuário de teste, aprovamos imediatamente
    if api_user.lower() == "teste":
        return None

    url = TRACKER_API_URL.format(user=api_user, token=api_token, codigo="LX000000000BR")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 401:
                    return "invalid_api_key"
                return None
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return "cannot_connect"


class CorreiosTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._packages = []

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Janela inicial de configuração."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors = {}
        if user_input is not None:
            api_user = user_input.get("api_user", "").strip()
            api_token = user_input.get(CONF_API_KEY, "").strip()

            # Se o utilizador deixar em branco, preenchemos com os dados de teste públicos
            if not api_user or not api_token:
                api_user = "teste"
                api_token = "1abcd00b2731640e886fb41a8a9671ad1434c599dbaa0a0de9a5aa619f29a83f"

            error = await _test_api_key(api_user, api_token)
            if error:
                errors["base"] = error
            else:
                # Juntamos os dois para guardar no formato que o Coordinator já entende (user|token)
                combined_key = f"{api_user}|{api_token}"
                return self.async_create_entry(
                    title="Correios Tracker",
                    data={CONF_API_KEY: combined_key, CONF_PACKAGES: []},
                )

        # Formulário com campos separados (ambos opcionais para permitir o modo de teste)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional("api_user", default=""): str,
                vol.Optional(CONF_API_KEY, default=""): str
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return CorreiosTrackerOptionsFlow(entry)


class CorreiosTrackerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry
        self._packages = list(entry.options.get(CONF_PACKAGES, entry.data.get(CONF_PACKAGES, [])))

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            action = user_input["action"]
            if action == "Adicionar":
                return await self.async_step_add()
            elif action == "Remover":
                return await self.async_step_remove()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("action", default="Adicionar"): vol.In(["Adicionar", "Remover"])
            }),
            description_placeholders={"summary": f"Você tem {len(self._packages)} pacote(s) monitorado(s)."},
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
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=15, max=10000)
                ),
            }),
            errors=errors,
        )

    async def async_step_remove(self, user_input: dict | None = None) -> FlowResult:
        if not self._packages:
            return self.async_abort(reason="no_packages")

        options = {
            p[CONF_TRACKING_CODE]: f"{p.get(CONF_DESCRIPTION, p[CONF_TRACKING_CODE])} ({p[CONF_TRACKING_CODE]})"
            for p in self._packages
        }

        if user_input is not None:
            code = user_input["remove_code"]
            self._packages = [p for p in self._packages if p[CONF_TRACKING_CODE] != code]
            return self.async_create_entry(title="", data={CONF_PACKAGES: self._packages})

        return self.async_show_form(
            step_id="remove",
            data_schema=vol.Schema({
                vol.Required("remove_code"): vol.In(options)
            }),
        )