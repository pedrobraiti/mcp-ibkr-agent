# Contribuindo

Obrigado pelo interesse! Este é um projeto de **encanamento de trading** — mudanças que
afetam a execução de ordens exigem cuidado redobrado.

## Setup

```bash
python -m venv .venv
# Windows (PowerShell): & ".venv\Scripts\Activate.ps1"
# Linux/macOS:          source .venv/bin/activate
pip install -e ".[dev]"
```

## Antes de abrir um PR

- `ruff check .` (lint) e `pytest -q` (testes) precisam passar — o CI roda os dois.
- Cubra com testes qualquer lógica nova. Os testes rodam **sem rede** (respx/fakes),
  então não dependem do gateway nem da conta.
- **Nunca** inclua segredos, account ids reais ou dados de conta em código, testes ou logs.

## Estilo

- Commits no padrão [Conventional Commits](https://www.conventionalcommits.org/):
  `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`.
- Mensagens no imperativo, explicando o **porquê** quando não for óbvio.

## Arquitetura

Hexagonal (ports & adapters): trocar/estender broker ou fonte de dados vive em
`adapters/` + `server/services.py`; o domínio (`domain/`) não conhece a IBKR.
Veja o [README](README.md) para o panorama.
