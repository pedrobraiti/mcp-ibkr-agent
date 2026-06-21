# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-06-21 (setup inicial)

## Onde parei
Acabei de rodar o `/setup`: criei a estrutura `.claude/` (context, decisions, todo, handoff), `CLAUDE.md`, `README.md`, configs de git (`.gitignore`, `.gitattributes`, `.editorconfig`), inicializei o git, fiz o commit inicial e criei o repositório PÚBLICO no GitHub `mcp-ibkr-agent`. Nenhum código de aplicação foi escrito ainda.

## Contexto mental
Arquitetura já está 100% travada após pesquisa (ver `.claude/decisions.md`):
- **CPAPI (Client Portal API REST), não TWS/ib_async** — porque fracionário de ação só funciona oficialmente via CPAPI com o campo `cashQty` (ordem por valor em US$).
- **Hexagonal (ports & adapters):** BrokerPort, MarketDataPort, AuthPort; tudo sobre CPAPI agora, ib_async fica como adapter de dados futuro opcional.
- **Auth:** OAuth headless é o alvo, mas com fallback de Gateway (login manual) porque OAuth retail pode exigir liberação da IBKR.
- **Segurança:** paper primeiro (conta `U24235856`), live atrás de flag + dry-run + confirmação + limite.
- Reaproveitar `services/ib_service.py` do quick_invest como referência (já é CPAPI), mas reescrever limpo.

## Próximo passo concreto
Montar o scaffold: criar `.venv` (Python 3.12+), `pyproject.toml`/`requirements.txt`, e a árvore de pastas hexagonal (`domain/`, `adapters/`, `mcp/`, `tests/`). Antes, vale conferir a doc viva da CPAPI (formato exato do corpo da ordem com `cashQty` e o fluxo de auth do Gateway) — se precisar de pesquisa profunda, mandar prompt para o usuário levar à IA de pesquisa (ver CLAUDE.md).

## Em aberto / armadilhas
- Confirmar disponibilidade do OAuth para conta varejo pessoal na IBKR (pode bloquear o headless puro → por isso o fallback Gateway).
- Validar empiricamente no paper se a permissão "Trade in Fractions" espelha da live e se `cashQty` funciona na conta paper.
- CPAPI exige o Client Portal Gateway rodando localmente (Java) + sessão logada; a market data snapshot às vezes vem vazia na 1ª chamada (precisa "aquecer"/repetir).
- `.env` real do quick_invest tem segredos — NÃO copiar para este repo público; só espelhar chaves no `.env.example`.

## Como retomar rápido
- Ler `.claude/decisions.md` para o "porquê" de cada escolha.
- Referência de código CPAPI: `G:\Meu Drive\vscode\quick_invest\services\ib_service.py`.
- Repo: GitHub `pedrobraiti/mcp-ibkr-agent` (público).
