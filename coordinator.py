"""Coordinator de rastreamento por pacote."""
from __future__ import annotations

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
        url = TRACKER_API_URL
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Apikey {self.api_key}",
        }
        payload = {"code": self.tracking_code}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 401:
                        raise UpdateFailed("Chave de API inválida")
                    if resp.status == 404:
                        return self._empty("Objeto não encontrado")
                    if resp.status != 200:
                        raise UpdateFailed(f"Erro HTTP {resp.status}")
                    data = await resp.json()
                    # API Wonca retorna dados num campo "json" como string
                    if json_str := data.get("json"):
                        import json as json_module
                        data = json_module.loads(json_str)
                    _LOGGER.debug("Resposta API [%s]: %s", self.tracking_code, data)
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
            "location_raw": None,
            "last_update": None,
            "events": [],
        }

    def _parse(self, data: dict) -> dict[str, Any]:
        result = self._empty("Sem informações")

        # API Wonca pode retornar directamente o objeto ou dentro de uma lista
        obj = data.get("object") or data.get("objeto") or data
        if isinstance(obj, list):
            obj = obj[0] if obj else {}

        if not obj:
            result["status"] = data.get("message", "Sem informações")
            return result

        # Status de erro da API
        if obj.get("erro"):
            result["status"] = obj.get("mensagem", "Erro na API")
            return result

        # Tenta diferentes campos de status
        eventos = obj.get("eventos") or []
        evento = eventos[0] if eventos else {}
        
        if evento:
            result["status"] = evento.get("descricao") or evento.get("descricaoWeb") or "Sem informações"
            
            # Handle datetime format from Wonca API
            dt = evento.get("dtHrCriato") or evento.get("dtHrCriado")
            if isinstance(dt, dict):
                result["last_update"] = dt.get("date")
            else:
                result["last_update"] = dt

            # Local format
            unidade = evento.get("unidade") or {}
            endereco = unidade.get("endereco", {}) if isinstance(unidade, dict) else {}
            if isinstance(endereco, dict):
                loc_text = f"{unidade.get('nome', '')} - {endereco.get('cidade', '')}/{endereco.get('uf', '')}"
            elif isinstance(unidade, str):
                loc_text = unidade
            else:
                loc_text = None
            result["location"] = loc_text

            desc_lower = (evento.get("descricao") or "").lower()
            result["is_delivered"] = any(s in desc_lower for s in DELIVERED_STATUSES)

        parsed_events = []
        for e in eventos:
            dt = e.get("dtHrCriado") or e.get("dtHrCriato")
            if isinstance(dt, dict):
                dt = dt.get("date")
            parsed_events.append({
                "data": dt or "",
                "status": e.get("descricao") or e.get("descricaoWeb") or "",
                "local": e.get("unidade", {}).get("endereco", {}).get("cidade", "") if isinstance(e.get("unidade"), dict) else "",
            })
        result["events"] = parsed_events

        return result
