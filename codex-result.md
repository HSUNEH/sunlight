CODEX_PROMPT.md 실행 완료.

변경 사항
- `src/app.py`: PDF 페이지에 bbox hover용 SVG 레이어 추가 (PDF hover → 번역 하이라이트)
- `src/app.py`: 번역 하이라이트용 JS 함수(`highlightTranslation`, `clearTranslationHighlight`) 추가
- `src/app.py`: `.para.highlight` 스타일 추가

수동 확인
1) test.pdf 업로드 → 번역
2) PDF에서 텍스트 영역 hover 시 오른쪽 번역 문단 하이라이트 확인
3) 번역본 hover → PDF 하이라이트 기존 기능 유지 확인
