# Decisões arquiteturais/técnicas

Registro de decisões com o "porquê". Append-only — não edita entradas antigas.

<!-- Formato:
## YYYY-MM-DD — Título curto da decisão
**Motivo:** por que foi decidido assim.
**Alternativas consideradas:** o que ficou de fora e por quê.
-->

## 2026-06-21 — Interface = servidor MCP próprio
**Motivo:** o agente (Claude Code) chama tools nativas (get_balance, get_quote, get_positions, place_order, cancel_order, get_portfolio...) sem depender de Bash/CLI. Mais elegante e seguro para a skill `/invest`; é o "MCP do IBKR" que o usuário queria.
**Alternativas consideradas:** CLI em Python (mais simples, descartado por ser menos integrado); híbrido lib+CLI+MCP (overengineering para o início).

## 2026-06-21 — Conexão IBKR = Client Portal API (CPAPI), não TWS/ib_async
**Motivo:** o requisito firme de fracionário (aportes por valor em US$, DCA, rebalanceamento) só é oficialmente suportado via CPAPI usando o campo `cashQty` (changelog IBKR 27/03/2026). O TWS API/ib_async tem suporte ambíguo e historicamente quebrado para fracionário de equity (erros 10242/10243, quantidade decimal rejeitada/truncada). Insight: o quick_invest JÁ usava CPAPI — só mandava `quantity` (inteiro) em vez de `cashQty`. Logo, não é migração, é usar o campo certo.
**Alternativas consideradas:** ib_async/TWS (revertida — pior para fracionário); FIX API (institucional, fora de escopo).

## 2026-06-21 — Arquitetura hexagonal (ports & adapters), CPAPI-only por enquanto
**Motivo:** robustez e profissionalismo vêm do DESIGN, não de duplicar conexão. Definir `BrokerPort`, `MarketDataPort`, `AuthPort` e implementar tudo sobre CPAPI agora. Permite plugar um adapter de dados em ib_async no futuro sem reescrever nada.
**Alternativas consideradas:** híbrido CPAPI (execução) + ib_async (dados) AGORA — descartado: com OAuth headless exigiria 2 sessões headless + 2 usernames (regra "1 brokerage session por username") = foot-gun e ruim para repo público reproduzível.

## 2026-06-21 — Auth = OAuth headless como alvo, Gateway (login manual) como fallback
**Motivo:** objetivo final é schedule autônomo sem navegador → OAuth. Mas OAuth da Web API para conta varejo pessoal pode exigir solicitar acesso à IBKR (e há OAuth 1.0a mais complexo), o que não pode bloquear o início. Auth atrás de `AuthPort` com adapter de Gateway garantido permite rodar desde o dia 1 e trocar para OAuth depois.
**Alternativas consideradas:** Gateway-only (não atinge o objetivo headless); OAuth-only desde já (risco de bloqueio por liberação da IBKR).

## 2026-06-21 — Escopo = paper primeiro + trava dura para live
**Motivo:** segurança. Opera de fato na conta paper `U24235856`. `live` existe atrás de flag explícita, com dry-run como padrão, confirmação obrigatória e limite de valor.
**Alternativas consideradas:** só leitura/simulação primeiro (lento demais); paper-only sem caminho p/ live (não atende objetivo final).
