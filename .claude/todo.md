# TODO

Plano vivo do projeto. Tarefas e subtarefas, marcadas conforme concluídas.

## Em progresso
- [ ] Camada de segurança (`safety/`) — paper/live flag, dry-run padrão, limite de valor (MAX_ORDER_VALUE), checagem de RTH

## Próximas
- [ ] Servidor MCP (`server/`) — expor as tools sobre os ports (verificar SDK `mcp` via Context7)
- [ ] Wiring/composição — montar client+auth+market_data+broker a partir de Settings; loop de tickle em background
- [ ] README com instruções de setup (gateway, username dedicado, habilitar fracionário) e de rodar o MCP
- [ ] (Futuro) adapter de dados ib_async no MarketDataPort
- [ ] (Descartado) OAuth — IBKR não libera p/ varejo (ver decisions.md)

## Concluído
- [x] Setup inicial do projeto
- [x] Estudo do quick_invest e definição da arquitetura (ver decisions.md)
- [x] Scaffold hexagonal (pyproject, .venv 3.12, estrutura de pastas src/ibkr_agent)
- [x] `domain/` — modelos (OrderRequest quantity|cash_qty, Quote, Position, AccountSummary, OrderResult) + ports (BrokerPort, MarketDataPort, AuthPort) + testes do domínio (5 passando)
- [x] `config.py` (pydantic-settings) + `.env.example` (sem OAuth, doc de gateway/username dedicado)
- [x] `adapters/cpapi/` — client (httpx, base_url normalizado, verify=False), GatewayAuth (status/ssodh-init/tickle/accounts), MarketData (resolve_conid c/ cache, get_quote c/ warmup, summary, positions paginado), Broker (place_order cashQty|quantity + loop de reply c/ allow-list, cancel, live orders). 11 testes passando (respx), ruff limpo
