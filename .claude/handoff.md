# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-06-21 (adapter CPAPI completo)

## Onde parei
Adapter CPAPI inteiro implementado e testado (11 testes passando, ruff limpo). Pronto:
- `config.py` — Settings via pydantic-settings (CPAPI, modo paper/live, dry-run, max_order_value, tickle).
- `adapters/cpapi/client.py` — httpx async; base_url normalizado com barra final + endpoint sem barra inicial (senão httpx descarta `/v1/api`); `verify=False`; erros em `CpapiError`.
- `adapters/cpapi/auth.py` — `GatewayAuth` (AuthPort): status, ssodh/init quando connected-mas-não-auth, tickle, `/iserver/accounts`.
- `adapters/cpapi/market_data.py` — `CpapiMarketData` (MarketDataPort): resolve_conid (filtra US, com cache), get_quote (warmup duplo do snapshot, fields 31/84/86), get_account_summary, get_positions (paginado).
- `adapters/cpapi/broker.py` — `CpapiBroker` (BrokerPort): place_order (monta cashQty OU quantity + cOID idempotente), **loop de reply com allow-list** (default só `o354`; warning desconhecido BLOQUEIA), cancel_order, get_live_orders.
Tudo commitado e no GitHub.

## Contexto mental
Arquitetura travada (ver `.claude/decisions.md`). **OAuth foi DESCARTADO** — IBKR não libera p/ varejo; auth é só Gateway+tickle. Decisões críticas do adapter vieram do relatório de pesquisa da CPAPI: endpoint de ordem é `POST /iserver/account/{acct}/orders` com array `orders`; resposta costuma ser pergunta de precaução → `POST /iserver/reply/{id}` `{"confirmed":true}` em loop; snapshot e `/iserver/account/orders` precisam de chamada dupla (warmup); `/iserver/accounts` obrigatório antes de operar; rate limit 10 req/s; manutenção diária ~01:00; username dedicado (competing session).

## Próximo passo concreto
Implementar `safety/` (camada que envolve o BrokerPort): bloquear live a menos que `trading_allow_live=true`; `dry_run` por padrão (não envia ordem, retorna OrderResult com dry_run=true); recusar ordem acima de `max_order_value` (p/ cashQty é direto; p/ quantity precisa do preço via MarketDataPort → calcular notional); checar RTH (fracionário só em pregão). Depois: `server/` MCP (verificar SDK `mcp` no Context7 antes de escrever) e o wiring a partir de Settings com loop de tickle em background.

## Em aberto / armadilhas
- Nomes de campo de `/portfolio/{acct}/summary` e `/positions` podem variar por conta → VALIDAR no paper e fixar.
- Validar no paper: permissão "Trade in Fractions" espelhada, cashQty funcionando, e qual nível de market data a conta tem (afeta warning o354).
- allow-list de reply: hoje só `o354`. Ao testar no paper, mapear quais outros warnings são benignos antes de adicioná-los.
- Repo PÚBLICO: segredos só no `.env` local (gitignored).

## Como retomar rápido
- Rodar testes: `.venv/Scripts/python.exe -m pytest -q` | lint: `.venv/Scripts/python.exe -m ruff check .`
- Estrutura: `src/ibkr_agent/{domain,adapters/cpapi,safety,server}/`.
- Referência (legado, já reescrito): `G:\Meu Drive\vscode\quick_invest\services\ib_service.py`.
- Relatórios de pesquisa (CPAPI + fracionário) estão no histórico desta conversa — se precisar de mais pesquisa, escrever prompt p/ o usuário (ver CLAUDE.md).
