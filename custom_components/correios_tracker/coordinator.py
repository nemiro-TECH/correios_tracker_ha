"""Coordinator de rastreamento por pacote."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL, DELIVERED_STATUSES, DOMAIN, TRACKER_API_URL

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

        cidade_uf = f"{cidade}/{uf}" if cidade and uf else cidade or uf

        if nome and cidade_uf:
            text = f"{nome} — {cidade_uf}"
        elif nome:
            text = nome
        else:
            text = cidade_uf

        return text if text else None, raw
    return None, None

class CorreiosDataCoordinator(DataUpdateCoordinator[dict]):
    """Classe para gerenciar a atualização assíncrona de um pacote."""

    def __init__(
        self,
        hass: HomeAssistant,
        tracking_code: str,
        description: str,
        api_key: str,
        scan_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        """Inicializa o coordenador."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Correios {tracking_code}",
            update_interval=timedelta(minutes=scan_interval),
        )
        self.tracking_code = tracking_code.upper()
        self.description = description
        self.api_key = api_key

    async def _update_data(self) -> dict:
        # Permite usar uma conta própria ou o fallback público de testes
        if "|" in self.api_key:
            user, token = self.api_key.split("|", 1)
        else:
            # Usuário de teste público (pode sofrer limite de tráfego em horas de ponta)
            user = "teste"
            token = "1abcd00b2731640e886fb41a8a9671ad1434c599dbaa0a0de9a5aa619f29a83f"

        url = TRACKER_API_URL.format(user=user, token=token, codigo=self.tracking_code)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 429:
                        _LOGGER.warning("Rate limit atingido na API Link&Track.")
                        return self.data or self._empty("Rate limit atingido")
                        
                    resp.raise_for_status()
                    data = await resp.json()
                    return self._parse(data)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Erro de conexão com Link&Track: {err}")

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

        eventos = data.get("eventos", [])
        if not eventos:
            result["status"] = "Aguardando postagem ou não encontrado"
            return result

        # O primeiro evento da lista é sempre o mais recente
        evento_recente = eventos[0]
        
        result["status"] = evento_recente.get("status", "Sem informações")
        result["last_update"] = f"{evento_recente.get('data', '')} às {evento_recente.get('hora', '')}"
        result["location"] = evento_recente.get("local")
        result["location_raw"] = None
        
        desc_lower = result["status"].lower()
        result["is_delivered"] = any(s in desc_lower for s in DELIVERED_STATUSES)

        parsed_events = []
        for e in eventos:
            parsed_events.append({
                "data": f"{e.get('data', '')} às {e.get('hora', '')}",
                "status": e.get("status", ""),
                "local": e.get("local", ""),
            })
            
        result["events"] = parsed_events
        return result