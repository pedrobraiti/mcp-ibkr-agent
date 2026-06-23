<!-- Thanks for contributing to Valet. Keep PRs focused and small where possible. -->

## What & why

<!-- What does this change and what problem does it solve? Link any issue. -->

## How it was tested

- [ ] `ruff check .` passes
- [ ] `pytest -q` passes
- [ ] If it touches order execution, describe how it was validated (paper/live, dry-run, or offline tests)

## Safety checklist

- [ ] No secrets, account ids, or `.env` values committed
- [ ] Defaults stay safe (`paper`, `dry_run=true`, `allow_live=false`) — no silent loosening
- [ ] New config keys are mirrored in `.env.example`
