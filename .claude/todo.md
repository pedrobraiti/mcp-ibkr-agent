# TODO

Plano vivo do projeto. Tarefas e subtarefas, marcadas conforme concluídas.

## Em progresso
- (nada em andamento — próxima tarefa abaixo)

## Próximas
- [ ] Ao BLOQUEAR um warning fora da allow-list, enviar `Decline` (`reply` com `confirmed:false`) em vez de só não responder — hoje deixa uma ordem `Inactive` órfã na conta (vista no teste: 864501251/520/523)
- [ ] No `sell` por valor em US$: converter dólar→ações via cotação (cashQty não vale p/ venda); para "vender tudo" usar a quantidade exata da posição (evita o warning `o2137`)
- [ ] Loop de `tickle` em background + monitor que avisa quando a sessão cair (reautenticar)
- [ ] Tratar feriados no `is_market_open_now` (calendário de mercado)
- [ ] Polir precisão de positions (mktPrice/avgCost vêm como float) quando houver posições reais
- [ ] (Futuro) acompanhar preenchimento de ordem (status Filled) e P&L pós-venda
- [ ] (Descartado) OAuth — IBKR não libera p/ varejo; auth só Gateway (ver decisions.md)

## Concluído
- [x] Setup inicial do projeto
- [x] Estudo do quick_invest e definição da arquitetura (ver decisions.md)
- [x] Scaffold hexagonal (pyproject, .venv 3.12, estrutura de pastas src/ibkr_agent)
- [x] `domain/` — modelos (OrderRequest quantity|cash_qty, Quote, Position, AccountSummary, OrderResult) + ports (BrokerPort, MarketDataPort, AuthPort) + testes do domínio (5 passando)
- [x] `config.py` (pydantic-settings) + `.env.example` (sem OAuth, doc de gateway/username dedicado)
- [x] `adapters/cpapi/` — client (httpx, base_url normalizado, verify=False), GatewayAuth (status/ssodh-init/tickle/accounts), MarketData (resolve_conid c/ cache, get_quote c/ warmup, summary, positions paginado), Broker (place_order cashQty|quantity + loop de reply c/ allow-list, cancel, live orders). 11 testes passando (respx), ruff limpo
- [x] `safety/` — GuardedBroker (decorator do BrokerPort): live lock, dry-run padrão, limite de valor (notional via quote p/ quantity), RTH; market_hours. Testes com fakes
- [x] `server/` — FastMCP (mcp 1.28) com tools (session_status, market_status, get_quote, account_summary, positions, buy, sell, cancel_order, open_orders) + composition root (build_services); console script `mcp-ibkr-agent`. Smoke tests. 19 testes no total
- [x] README completo (setup gateway, username dedicado, fracionário, registro no Claude Code) + LICENSE MIT
- [x] VALIDAÇÃO REAL: sistema testado contra a conta live U24235856 — auth/connected OK, supportsCashQty/supportsFractions=True (Pro), saldo US$8.87, cotação e posições funcionando. Build de 2023 não é problema (serverVersion runtime = 10.46.1l Jun/2026)
- [x] `healthcheck` (módulo + console script `ibkr-healthcheck`): relatório de conexão/conta/saldo. Fix de precisão de saldo (arredonda p/ centavos) e de encoding (sem emoji, console Windows cp1252)
- [x] `config.py` acha o `.env` por caminho ABSOLUTO (funciona quando o Claude Code lança o MCP de outro CWD)
- [x] MCP `ibkr` REGISTRADO no Claude Code (escopo local, `claude mcp add`) — status Connected. Tools aparecem numa sessão NOVA
- [x] TESTE DE ORDEM REAL (mercado aberto, conta real): round-trip US$2 em AAPL. BUY via `cashQty` executou (0.0066 @ 298.96); allow-list de reply mapeada ao vivo (`o354`+`o10164`+`o10223`+`o10151`+`o10153`). Descoberta: `cashQty` é buy-only → venda fechada por quantidade fracionária exata (0.0066 @ 300.41); caixa recuperado (US$8.84, flat). Ver decisions.md 2026-06-22
- [x] Venda fracionária: `OrderRequest.quantity` de `int` → `Decimal`; broker envia `float(quantity)`; guard de notional com Decimal; tools `buy`/`sell` aceitam quantidade fracionária (`sell` sem `cash_amount`, inválido na IBKR); nova tool `close_position(symbol)` que lê o tamanho exato e fecha 100%. Testes novos (fracionário no model e no broker; close_position no server). 21 testes, ruff limpo
- [x] VALIDAÇÃO WIRED ao vivo (mercado aberto): chamadas reais das funções `buy`/`sell`/`close_position` do app. `buy` US$2 e `sell` 0.0066 passaram (round-trip, flat). `close_position` revelou fragilidade: depende do `/portfolio/positions`, eventualmente-consistente (ficou 0.0 por 30s+ após a compra). Endurecido: `get_positions` filtra linhas com quantidade 0 (também conserta contagem fantasma do healthcheck); novo `invalidate_positions()`; `close_position` invalida antes de ler e retorna mensagem honesta sobre o lag. 22 testes, ruff limpo
- [x] Keep-alive `/tickle` + alerta de reauth: componente `session/SessionKeeper` (tickle no intervalo; recuperação leve via ensure_session quando connected-sem-auth; alerta sem spam quando cai) + runnable `python -m ibkr_agent.keepalive` (console script `ibkr-keepalive`) com bip e mensagem `[ALERTA]`. Testes unitários (5) + smoke ao vivo (tickle real, sem alerta). README com seção "Mantendo a sessão viva". 27 testes, ruff limpo
