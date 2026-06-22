# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento conforme [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.0] - 2026-06-22

Primeira versão funcional, validada ao vivo contra uma conta IBKR real.

### Adicionado
- Servidor **MCP** (FastMCP) com 10 tools: `session_status`, `market_status`,
  `get_quote`, `account_summary`, `positions`, `buy`, `sell`, `close_position`,
  `cancel_order`, `open_orders`.
- **Compra fracionária** por valor em US$ (`cashQty`) e **venda/fechamento fracionário**
  por quantidade de ações (incl. `close_position`, que lê o tamanho exato da posição).
- Arquitetura **hexagonal** (domain / adapters / safety / server) sobre a Interactive
  Brokers Client Portal API (REST).
- **Travas de segurança**: paper-first, dry-run por padrão, *live lock*, limite de valor
  por ordem, horário de pregão (RTH) com **feriados da NYSE**, e allow-list de warnings
  de confirmação (com *decline* automático ao bloquear um warning desconhecido).
- **Keep-alive** de sessão com alerta de reautenticação (`ibkr-keepalive`).
- **Healthcheck** de conexão/conta (`ibkr-healthcheck`).

[0.1.0]: https://github.com/pedrobraiti/mcp-ibkr-agent/releases/tag/v0.1.0
