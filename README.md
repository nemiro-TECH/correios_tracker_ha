# Correios Tracker para Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/nemiro-TECH/correios_tracker_ha)](https://github.com/nemiro-TECH/correios_tracker_ha/releases)

<<<<<<< HEAD
Uma integração personalizada (Custom Component) robusta e assíncrona para rastrear encomendas dos Correios diretamente no Home Assistant, utilizando a API do [SiteRastreio](https://www.siterastreio.com.br/).
=======


> 🎨 **Interface Gráfica:** Para a melhor experiência visual no seu painel (dashboard), utilize o nosso cartão Lovelace oficial: [Correios Tracker Card](https://github.com/nemiro-TECH/correios_tracker_card).

---

## ✨ Funcionalidades

- **Configuração 100% via UI:** Sem necessidade de editar ficheiros `configuration.yaml`.
- **Organização por Dispositivos (Devices):** Cada encomenda é agrupada num "Dispositivo" contendo as suas respetivas entidades, facilitando a gestão.
- **Entidades Detalhadas:**
  - `sensor.[codigo]_status`: Mostra o status atual e possui atributos ricos (`localizacao`, `movimentacoes`, `ultima_atualizacao`).
  - `binary_sensor.[codigo]_entregue`: Sensor binário (`on`/`off`) perfeito para criar automações simples de "Entregue" ou "Em trânsito".
- **Gestão via Serviços:** Adicione e remova pacotes através dos serviços `correios_tracker.add_package` e `correios_tracker.remove_package` sem precisar reiniciar o sistema.

---

## 🔑 Pré-requisitos

Esta integração consome a API RESTful do SeuRastreio para garantir estabilidade e evitar bloqueios de IP (captchas) comuns no site dos Correios.
1. Aceda a [seurastreio.com.br](https://siterastreio.com.br/) e crie uma conta gratuita.
2. Vá ao Dashboard > **Chaves de API**.
3. Gere uma nova chave. Vai precisar dela durante a instalação no Home Assistant.

---

## 🛠️ Instalação

### Opção 1: Via HACS (Recomendado)

O [HACS](https://hacs.xyz/) é a melhor forma de manter a sua integração atualizada automaticamente.

[![Adicionar ao HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nemiro-TECH&repository=correios_tracker_ha&category=integration)

**Instalação Manual no HACS:**
1. Abra o **HACS** no seu Home Assistant.
2. Navegue até à secção **Integrações**.
3. Clique nos três pontos (`⋮`) no canto superior direito e selecione **Repositórios personalizados**.
4. Adicione o URL: `https://github.com/nemiro-TECH/correios_tracker_ha` e escolha a categoria **Integração**.
5. Clique em **Adicionar** e, de seguida, clique em **Transferir** (Download).
6. **Reinicie o Home Assistant.**

### Opção 2: Instalação Manual (Avançado)
1. Faça o download do repositório (ficheiro `.zip` da última Release).
2. Extraia o conteúdo e copie a pasta `correios_tracker` para dentro do diretório `custom_components/` do seu Home Assistant.
3. **Reinicie o Home Assistant.**

---

## ⚙️ Configuração

1. No Home Assistant, vá a **Configurações** > **Dispositivos e Serviços**.
2. Clique no botão **+ Adicionar Integração** no canto inferior direito.
3. Pesquise por **Correios Tracker**.
4. Insira a sua **Chave de API** gerada no SeuRastreio.
5. Siga as instruções no ecrã para adicionar o seu primeiro pacote (Código de Rastreio e Apelido).

Para adicionar ou remover pacotes posteriormente, basta clicar em **Configurar** no cartão da integração ou usar o painel Lovelace ([Correios Tracker Card](https://github.com/nemiro-TECH/correios_tracker_card)).

---

## 🤖 Exemplo de Automação

Como cada pacote cria um sensor com o histórico de movimentações, é muito fácil criar automações para ser notificado quando o estado de entrega muda.

**Notificação quando a encomenda "Saiu para entrega":**
```yaml
alias: "Notificação: Encomenda Saiu para Entrega"
description: "Avisa no telemóvel quando os Correios saem para entregar um pacote"
trigger:
  - platform: state
    entity_id: sensor.correios_aa123456789br_status
    to: "Objeto saiu para entrega ao destinatário"
action:
  - service: notify.notify
    data:
      title: "📦 Encomenda a Caminho!"
      message: "A sua encomenda ({{ state_attr('sensor.correios_aa123456789br_status', 'descricao') }}) saiu para entrega hoje!"
mode: single