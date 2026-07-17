# Contributing

Thanks for taking a look! This is an open pet project — issues and pull requests are welcome.

## Development setup

```bash
uv sync
uv run pre-commit install
cp .env.example .env        # then set SECRET_KEY and DATABASE_URL
uv run pytest tests/ -v
```

See the [README](README.md) for the full run instructions (plain `uv` or Docker).

## Workflow

- Direct commits to `main` are blocked. Work in a branch and open a pull request.

  ```bash
  git checkout -b feature/my-change
  git commit                 # pre-commit runs automatically
  git push origin feature/my-change
  ```

- Every push and PR runs CI: tests (Python 3.13 / 3.14), lint & type-check
  (ruff, mypy, prettier), and a dependency audit. All checks must pass.
- Keep pull requests focused and small where possible.

## Code style

- Formatting and linting are enforced by pre-commit (`ruff`, `ruff-format`,
  `prettier`). Run `uv run pre-commit run --all-files` before pushing.
- Type hints are required — `mypy` runs in CI.
- Add or update tests for any behaviour change.

## Reporting bugs

Open an issue using the templates in `.github/ISSUE_TEMPLATE/`. Include steps to
reproduce, the expected result, and what actually happened.
