"""Constantes do Correios Tracker."""

DOMAIN = "correios_tracker"
DEFAULT_UPDATE_INTERVAL = 120  # Minutos

CONF_API_KEY = "api_key"
CONF_TRACKING_CODE = "tracking_code"
CONF_DESCRIPTION = "description"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PACKAGES = "packages"

TRACKER_API_URL = "https://seurastreio.com.br/api/public/rastreio/{codigo}"

DELIVERED_STATUSES = ["entregue ao destinatário", "objeto entregue", "entregue"]

ATTR_TRACKING_CODE = "codigo_objeto"
ATTR_DESCRIPTION = "descricao"
ATTR_LAST_UPDATE = "ultima_atualizacao"
ATTR_LOCATION = "localizacao"
ATTR_EVENTS = "movimentacoes"