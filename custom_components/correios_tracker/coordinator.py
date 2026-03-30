"""Coordinator de rastreamento por pacote."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL, DELIVERED_STATUSES, DOMAIN, SEURASTREIO_API_URL

_LOGGER = logging.getLogger(__name__)


def _parse_location(local: Any) -> tuple[str | None, dict | None]:
    """
    Extrai (string_formatada, objeto_bruto) do campo 'local' da API.

    A API pode retornar:
      - dict: {"nome": "...", "cidade": "...", "uf": "...", "bairro": "..."}
      - str: já formatado
      - None / ausente
    Retorna (texto_legível, raw_dict).
    """
    if local is None:
        return None, None

    if isinstance(local, str):
        return local if local.strip() else None, None

    if isinstance(local, dict):
        raw = local
        nome   = (local.get("nome")   or "").strip()
        cidade = (local.get("cidade") or "").strip()
        uf     = (local.get("uf")     or "").strip()
        bairro = (local.get("bairro") or "").strip()

        # Fallback em cascata
        cidade_uf = f"{cidade}/{uf}" if cidade and uf else cidade or uf

        if nome and cidade_uf:
            text = f"{nome} — {cidade_uf}"
        elif nome:
            text = nome
        elif cidade_uf:
            text = cidade_uf
        elif bairro:
            text = bairro
        else:
            text = None

        return text, raw

    return None, None


class CorreiosDataCoordinator(DataUpdateCoordinator):
    """Coordinator de dados para um pacote específico."""

    def __init__(
        self,
        hass: HomeAssistant,
        tracking_code: str,
        description: str,
        api_key: str,
        scan_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        self.tracking_code = tracking_code.upper().strip()
        self.description = description or tracking_code
        self.api_key = api_key

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.tracking_code}",
            update_interval=timedelta(minutes=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        url = SEURASTREIO_API_URL.format(codigo=self.tracking_code)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 401:
                        raise UpdateFailed("Chave de API inválida")
                    if resp.status == 404:
                        return self._empty("Objeto não encontrado")
                    if resp.status != 200:
                        raise UpdateFailed(f"Erro HTTP {resp.status}")
                    data = await resp.json()
                    _LOGGER.debug("Resposta API [%s]: %s", self.tracking_code, data)
                    return self._parse(data)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        raise UpdateFailed(f"Erro de conexão ou tempo esgotado com SeuRastreio: {err}")

    def _empty(self, status: str) -> dict:
        return {
            "tracking_code": self.tracking_code,
            "description": self.description,
            "status": status,
            "is_delivered": False,
            "location": None,
            "location_raw": None,
            "last_update": None,
            "events": [],
        }

    def _parse(self, data: dict) -> dict[str, Any]:
        result = self._empty("Sem informações")

        if not data.get("success"):
            result["status"] = data.get("message", "Sem informações")
            return result

        evento = data.get("eventoMaisRecente", {}) or {}
        if evento:
            result["status"] = evento.get("descricao") or "Sem informações"
            result["last_update"] = evento.get("data")

            loc_text, loc_raw = _parse_location(evento.get("local"))
            result["location"] = loc_text
            result["location_raw"] = loc_raw

            desc_lower = (evento.get("descricao") or "").lower()
            result["is_delivered"] = any(s in desc_lower for s in DELIVERED_STATUSES)

        # Lista completa de eventos
        parsed_events = []
        for e in (data.get("eventos") or []):
            loc_text, _ = _parse_location(e.get("local"))
            parsed_events.append({
                "data": e.get("data", ""),
                "status": e.get("descricao", ""),
                "local": loc_text or "",
            })
        result["events"] = parsed_events

        return result
