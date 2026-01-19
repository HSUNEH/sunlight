# Sunlight

논문 PDF를 파싱해 본문/테이블/수식/이미지를 분리하고, 필요 시 번역까지 이어지는 파이프라인을 제공합니다.

## 핵심 기능
- MinerU 기반 PDF 파싱
- 본문/테이블/수식/이미지 분리
- OpenAI 번역 연동 (본문만 번역)
- CLI 및 Gradio 웹 UI 제공

## 빠른 시작
```bash
source .venv/bin/activate
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

### CLI 실행
```bash
python -m src.cli test.pdf -o test_output.md --no-translate
python -m src.cli test.pdf -o test_translated.md -l ko
```

### 웹 UI 실행
```bash
python -m src.app
```
브라우저에서 http://localhost:7860 접속 후 PDF 업로드.

## 설정
- OpenAI API 키는 `.env`의 `OPENAI_API_KEY`로 관리합니다.

## 참고 문서
- `AGENTS.md`: 역할 분담 및 워크플로우
- `PLAN_PDF_PARSING.md`: 파싱 파이프라인 설계
- `CODEX_PROMPT.md`: 구현 지시 사항
