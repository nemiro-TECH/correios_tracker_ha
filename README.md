# Correios Tracker para Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Rastreamento de encomendas dos Correios no Home Assistant.

## Entidades criadas por pacote

| Entidade | Tipo | Descrição |
|---|---|---|
| `sensor.correios_{codigo}_status` | Sensor | Status atual do pacote (texto) |
| `binary_sensor.correios_{codigo}_entregue` | Binary Sensor | `on` = entregue, `off` = em trânsito |

## Instalação via HACS

1. HACS → Integrações → ⋮ → Repositórios personalizados
2. URL: `https://github.com/nemiro-TECH/correios_tracker_ha` | Tipo: Integração
3. Instalar → Reiniciar HA

## Configuração

1. Configurações → Integrações → + Adicionar → **Correios Tracker**
2. Gere sua chave gratuita em [seurastreio.com.br](https://seurastreio.com.br)
3. Insira a chave (apenas uma vez)
4. Adicione pacotes via:
   - Lovelace card (botão **+ Adicionar**)
   - Configurações → Integrações → Correios Tracker → Configurar

## Lovelace Card

Instale o card separado: [correios-tracker-card](https://github.com/nemiro-TECH/correios_tracker_card)

```yaml
type: custom:correios-tracker-card
```

## Automação de exemplo

```yaml
automation:
  alias: "Pacote entregue"
  trigger:
    platform: state
    entity_id: binary_sensor.correios_aa123456789br_entregue
    to: "on"
  action:
    service: notify.mobile_app_seu_celular
    data:
      title: "📦 Entregue!"
      message: "{{ states('sensor.correios_aa123456789br_status') }}"
```
