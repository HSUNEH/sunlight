# Repository Guidelines

## Project Structure & Module Organization
The repository is currently planning-focused. Source code is not yet checked in; the expected layout is documented in `PLAN_PDF_PARSING.md` and targets a Python module tree under `src/` with `parser/`, `models/`, and `utils/`, plus `tests/`. Current artifacts:
- `Agent.md` holds goals, milestones, and action items.
- `PLAN_PDF_PARSING.md` details the PDF parsing pipeline, proposed classes, and intended outputs (e.g., `content.md`, `tables/`, `figures/`).

## Build, Test, and Development Commands
No build system or task runner is defined yet. For local experiments aligned with the plan, the only documented command is:
```bash
pip install mineru
```
When a `requirements.txt` or scripts are added, update this section with exact install, run, and test commands (for example, `python -m pytest`).

## Coding Style & Naming Conventions
Python is the planned implementation language. Until style tooling is added, follow:
- 4-space indentation, UTF-8, and line length around 88–100 characters.
- `snake_case` for functions/variables, `PascalCase` for classes, and `test_*.py` for tests.
If formatting or linting is introduced (e.g., Black/Ruff), document the exact commands here.

## Testing Guidelines
Tests are planned under `tests/` with a `test_parser.py` entry point. No framework is configured yet; if using `pytest`, keep test names descriptive and include fixtures for sample PDFs. Document coverage expectations once benchmarks exist.

## Commit & Pull Request Guidelines
This directory is not a Git repository yet, so there is no commit history or convention to summarize. When Git is initialized, adopt a consistent message style (e.g., `feat: ...`, `fix: ...`) and require PRs to include a short description, related issue link, and parsing output samples or screenshots where applicable.

## Security & Configuration Tips
API keys (e.g., OpenAI) should live in environment variables or local config files excluded from version control. If adding `config.json` or `.env`, include a checked-in example such as `config.example.json`.
