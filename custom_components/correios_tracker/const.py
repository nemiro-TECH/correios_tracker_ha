"""Constantes do Correios Tracker."""

DOMAIN = "correios_tracker"
DEFAULT_UPDATE_INTERVAL = 60  # minutos

CONF_API_KEY = "api_key"
CONF_TRACKING_CODE = "tracking_code"
CONF_DESCRIPTION = "description"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PACKAGES = "packages"

# URL da API do Link&Track
TRACKER_API_URL = "https://api.linketrack.com/track/json?user={user}&token={token}&codigo={codigo}"

DELIVERED_STATUSES = [
    "entregue ao destinatário",
    "objeto entregue",
    "entregue",
]

ATTR_TRACKING_CODE = "codigo_objeto"
ATTR_DESCRIPTION = "descricao"
ATTR_LAST_UPDATE = "ultima_atualizacao"
ATTR_LOCATION = "localizacao"
ATTR_EVENTS = "movimentacoes"