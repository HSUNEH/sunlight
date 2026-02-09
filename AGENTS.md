# Repository Guidelines

## AI Agent

### Claude Code (Anthropic)
**역할: 모든 개발 작업 수행**

- 아키텍처 설계 및 구현 계획 수립
- 코드 작성 및 수정 (`src/` 포함)
- 테스트 실행 (`pytest`)
- 디버깅 및 오류 수정
- 코드 리뷰 및 문서 작성
- Git 커밋 및 푸시

### 실행 전 필수 설정
```bash
source .venv/bin/activate
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

### 현재 상태 (2026-01-19)
- MinerU v2.7.1 설치 완료
- MinerU 파서 구현 완료 (`src/parser/mineru_parser.py`)
- 번역 모듈 구현 완료 (`src/translator/openai_translator.py`)
- CLI 파이프라인 구현 완료 (`src/cli.py`)
- 테스트 통과: 2개 (parser + translator)
- 번역 테스트 성공: `test.pdf` → `test_translated.md`

### 사용법
```bash
source .venv/bin/activate
python -m src.cli <pdf> -o <output.md> -l ko
python -m src.cli <pdf> -o <output.md> --no-translate  # 번역 없이
```

### 알려진 이슈
- MinerU MPS/CPU 크래시 (NSRangeException)
- 임시 해결: 기존 output 재사용 (`output/{stem}/hybrid_auto/`)

### 다음 작업
1. 프론트엔드 설계 (VS Code Extension 또는 Web UI)
2. 원본-번역 하이라이트 동기화
3. QnA 세션 기능

---

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
