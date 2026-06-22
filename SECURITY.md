# Política de Segurança

Este projeto executa **ordens reais** em uma conta de corretora (Interactive Brokers).
Trate-o com o cuidado correspondente.

## Segredos e credenciais
- **Nunca** versione o arquivo `.env` (já está no `.gitignore`). Ele contém o ID da
  conta e configuração sensível. O `.env.example` (sem valores) é o que vai no repo.
- Não há chaves de API da IBKR no código: a autenticação é por **login manual** no
  Client Portal Gateway (sessão local). Não cole tokens/cookies de sessão em issues.
- Antes de abrir issue ou PR, confira que nenhum log colado contém account id, saldos
  ou identificadores de ordem reais.

## Padrões de segurança do código
- `paper`/dry-run por padrão; `live` exige `TRADING_ALLOW_LIVE=true` explícito.
- Limite de valor por ordem (`MAX_ORDER_VALUE`) e checagem de horário de pregão (RTH).
- Warnings de confirmação desconhecidos **bloqueiam** a ordem (não auto-confirmam).

## Reportando uma vulnerabilidade
Em vez de abrir uma issue pública, use os
[Security Advisories](https://github.com/pedrobraiti/mcp-ibkr-agent/security/advisories/new)
do GitHub (divulgação privada). Descreva o impacto e como reproduzir. Retornarei assim
que possível.
