# Contexto do projeto

> Camada **estável** da memória: o que o projeto é e suas características macro. Muda devagar.
> O detalhe volátil de "de onde parei" fica no `handoff.md`; as tarefas, no `todo.md`;
> as decisões com o porquê, no `decisions.md`.

**Nome:** mcp-ibkr-agent
**Descrição:** Servidor MCP que permite a um agente de IA (Claude Code) operar na Interactive Brokers — cotações, saldo, posições, P&L e ordens (inteiras e fracionárias via `cashQty`).
**Stack:** Python 3.12+, MCP server, Interactive Brokers Client Portal API (CPAPI/Web API REST).

## Visão geral
Sucessor limpo e profissional do projeto `quick_invest` (Telegram+GPT+IBKR, nunca testado de ponta a ponta). Aqui, quem analisa e decide é o próprio Claude Code: o usuário invoca uma skill `/invest` (manual hoje, schedule autônomo no futuro) e o Claude usa as tools deste MCP server para consultar mercado e executar compras/vendas na IBKR. A lógica de DECISÃO da skill (o que pesquisar, métricas, quando comprar/vender) é responsabilidade do usuário — este projeto entrega só o encanamento de trading confiável. Destino: repositório PÚBLICO no GitHub.

## Fase atual
Setup inicial — arquitetura travada, começando a construção.

## Restrições e bloqueios de longo prazo
- **Fracionário só via CPAPI + campo `cashQty`** (ordem por valor em US$). TWS API/ib_async é o caminho ruim p/ fracionário de ação (erros 10242/10243). Confirmado por pesquisa (changelog IBKR 27/03/2026).
- Fracionário exige permissão **"Trade in Fractions / Global"** habilitada na conta; ordens MKT durante regular trading hours (9:30–16:00 ET).
- CPAPI: 1 sessão de brokerage por username; sessão expira (~24h) → keep-alive `/tickle` ou OAuth.
- OAuth da Web API p/ conta varejo pessoal pode exigir solicitar acesso à IBKR — por isso há fallback de Gateway (login manual). VERIFICAR ao construir.
- Conta de teste paper: `U24235856`. Credenciais reaproveitadas do `.env` do quick_invest.
- Repo PÚBLICO → zero segredo versionado (`.env` no gitignore, `.env.example` espelhado sem valores).
