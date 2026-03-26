"""Coordinator de rastreamento por pacote."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL, DELIVERED_STATUSES, DOMAIN, SEURASTREIO_API_URL

_LOGGER = logging.getLogger(__name__)


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
                    return self._parse(data)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Erro de conexão: {err}") from err

    def _empty(self, status: str) -> dict:
        return {
            "tracking_code": self.tracking_code,
            "description": self.description,
            "status": status,
            "is_delivered": False,
            "location": None,
            "last_update": None,
            "events": [],
        }

    def _parse(self, data: dict) -> dict[str, Any]:
        result = self._empty("Sem informações")
        if not data.get("success"):
            result["status"] = data.get("message", "Sem informações")
            return result

        evento = data.get("eventoMaisRecente", {})
        if evento:
            result["status"] = evento.get("descricao", "Sem informações")
            result["location"] = evento.get("local")
            result["last_update"] = evento.get("data")
            desc_lower = (evento.get("descricao") or "").lower()
            result["is_delivered"] = any(s in desc_lower for s in DELIVERED_STATUSES)

        result["events"] = [
            {
                "data": e.get("data", ""),
                "status": e.get("descricao", ""),
                "local": e.get("local", ""),
            }
            for e in data.get("eventos", [])
        ]
        return result
