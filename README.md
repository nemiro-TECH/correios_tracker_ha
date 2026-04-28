# Correios Tracker para Home Assistant

Uma integração personalizada (Custom Component) robusta e assíncrona para rastrear encomendas dos Correios diretamente no Home Assistant, utilizando a API da [Wonca Labs](https://labs.wonca.com.br/).

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

Esta integração consome a API RESTful da Wonca Labs para garantir estabilidade e evitar bloqueios de IP (captchas) comuns no site dos Correios.

1. Aceda a [labs.wonca.com.br](https://labs.wonca.com.br/) e crie uma conta.
2. Gere uma chave de API. Vai precisar dela durante a instalação no Home Assistant.

---

## 🛠️ Instalação

Esta integração não está disponível no HACS. A instalação deve ser feita manualmente.

1. Faça o download do repositório (ficheiro `.zip` da última Release).
2. Extraia o conteúdo e copie a pasta `correios_tracker` para dentro do diretório `custom_components/` do seu Home Assistant.
3. **Reinicie o Home Assistant.**

---

## ⚙️ Configuração

1. No Home Assistant, vá a **Configurações** > **Dispositivos e Serviços**.
2. Clique no botão **+ Adicionar Integração** no canto inferior direito.
3. Pesquise por **Correios Tracker**.
4. Insira a sua **Chave de API** gerada na Wonca Labs.
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
```