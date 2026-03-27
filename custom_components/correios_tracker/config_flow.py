"""Config flow — valida API key antes de aceitar."""
from __future__ import annotations

import re
import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_KEY,
    CONF_DESCRIPTION,
    CONF_PACKAGES,
    CONF_SCAN_INTERVAL,
    CONF_TRACKING_CODE,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    SEURASTREIO_API_URL,
)

TRACKING_REGEX = re.compile(r"^[A-Z]{2}\d{9}[A-Z]{2}$")


async def _test_api_key(api_key: str) -> str | None:
    """Testa a chave de API. Retorna None se válida, ou string de erro."""
    # Usa um código de teste fictício — se retornar 401 a chave é inválida
    url = SEURASTREIO_API_URL.format(codigo="AA000000000BR")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 401:
                    return "invalid_api_key"
                # 200, 404, 422 etc → chave aceita pelo servidor
                return None
    except aiohttp.ClientError:
        return "cannot_connect"


def _valid_code(code: str) -> str:
    code = code.upper().strip()
    if not TRACKING_REGEX.match(code):
        raise vol.Invalid("invalid_tracking_code")
    return code


# ── Config Flow principal ────────────────────────────────────────────────────
class CorreiosTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY, "").strip()
            if not api_key:
                errors[CONF_API_KEY] = "api_key_required"
            else:
                error = await _test_api_key(api_key)
                if error:
                    errors[CONF_API_KEY] = error
                else:
                    await self.async_set_unique_id(DOMAIN)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Correios Tracker",
                        data={CONF_API_KEY: api_key},
                        options={CONF_PACKAGES: []},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(entry):
        return CorreiosOptionsFlow(entry)


# ── Options Flow — gerencia pacotes ─────────────────────────────────────────
class CorreiosOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry
        self._packages: list[dict] = list(entry.options.get(CONF_PACKAGES, []))

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            action = user_input["action"]
            if action == "add":
                return await self.async_step_add()
            if action == "remove":
                return await self.async_step_remove()
            return self.async_create_entry(title="", data={CONF_PACKAGES: self._packages})

        pkg_count = len(self._packages)
        actions = {"add": "➕ Adicionar pacote", "save": "✅ Fechar"}
        if pkg_count > 0:
            actions["remove"] = "🗑️ Remover pacote"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required("action"): vol.In(actions)}),
            description_placeholders={"summary": f"{pkg_count} pacote(s) monitorado(s)"},
        )

    async def async_step_add(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                code = _valid_code(user_input[CONF_TRACKING_CODE])
            except vol.Invalid:
                errors[CONF_TRACKING_CODE] = "invalid_tracking_code"
            else:
                if any(p[CONF_TRACKING_CODE] == code for p in self._packages):
                    errors[CONF_TRACKING_CODE] = "already_configured"
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
                    vol.Coerce(int), vol.Range(min=15, max=1440)
                ),
            }),
            errors=errors,
        )

    async def async_step_remove(self, user_input: dict | None = None) -> FlowResult:
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
            data_schema=vol.Schema({vol.Required("remove_code"): vol.In(options)}),
        )
