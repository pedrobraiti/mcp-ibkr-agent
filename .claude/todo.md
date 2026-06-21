# TODO

Plano vivo do projeto. Tarefas e subtarefas, marcadas conforme concluídas.

## Em progresso
- [ ] Definir scaffold do projeto (estrutura hexagonal de pastas, pyproject/requirements, .venv)

## Próximas
- [ ] `domain/` — modelos e portas (BrokerPort, MarketDataPort, AuthPort) + tipos de ordem (quantity vs cashQty)
- [ ] `adapters/cpapi/` — cliente CPAPI (auth Gateway, keep-alive /tickle, get_quote, get_balance, get_positions, place_order com cashQty/quantity, cancel_order)
- [ ] Camada de segurança — paper/live flag, dry-run padrão, confirmação e limite de valor
- [ ] Servidor MCP — expor as tools sobre os ports
- [ ] Testes unitários (lógica de domínio/segurança) + integração (adapter CPAPI mockado)
- [ ] `.env.example` espelhado, README com instruções de setup e de habilitar fracionário
- [ ] (Futuro) adapter OAuth no AuthPort; (futuro) adapter de dados ib_async

## Concluído
- [x] Setup inicial do projeto
- [x] Estudo do quick_invest e definição da arquitetura (ver decisions.md)
