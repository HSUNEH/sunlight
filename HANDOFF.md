# Handoff Document (2026-02-09)

## 프로젝트 개요
**sunlight** - 논문 PDF 번역기 + 원본-번역 하이라이트 동기화

## 기술 스택
- **PDF 파싱**: MinerU v2.7.1
- **번역**: OpenAI API (gpt-4o-mini)
- **프론트엔드**: Gradio
- **PDF 렌더링**: PyMuPDF (fitz)

## 프로젝트 구조
```
sunlight/
├── src/
│   ├── app.py              # Gradio 웹 앱 (메인)
│   ├── cli.py              # CLI 파이프라인
│   ├── parser/
│   │   ├── mineru_parser.py    # MinerU CLI 래퍼
│   │   ├── paragraph_builder.py # 블록 → Paragraph 변환
│   │   └── content_classifier.py
│   ├── translator/
│   │   └── openai_translator.py # 배치 번역 + async
│   └── models/
│       └── paper.py        # Paragraph, ParsedPaper 모델
├── tests/
├── output/                 # MinerU 파싱 결과 캐시
├── AGENTS.md              # AI 에이전트 역할 정의
├── CODEX_PROMPT.md        # Codex 지시서 (Claude가 작성)
├── codex-result.md        # Codex 실행 결과
└── 개발일지.md
```

## 완료된 기능

### 1. PDF 파싱 파이프라인
- MinerU로 PDF → JSON (content_list.json)
- bbox 좌표 보존 (`[x_min, y_min, x_max, y_max]`, 정규화×1000)

### 2. 번역
- 배치 번역 (25개씩)
- AsyncOpenAI 병렬 처리 (semaphore=3)
- 실패 시 개별 비동기 번역 fallback

### 3. Gradio 웹 앱
- 좌우 분할: PDF 이미지 | 번역본
- **양방향 하이라이트**:
  - 번역본 hover → PDF 하이라이트
  - PDF hover → 번역본 하이라이트
- JavaScript: `gr.Blocks(js=...)` 파라미터 사용 (gr.HTML 내 script 태그 안 됨)

### 4. 끊어진 문단 병합 (Cross-Column / Cross-Page Merging)
MinerU가 2칼럼 레이아웃이나 페이지 넘김에서 하나의 문장을 별도 블록으로 분리하는 문제 해결.

**병합 판단 로직:**
- 현재 블록 텍스트가 `.!?:;`로 끝나지 않으면 → 다음 블록과 병합
- `text_level == 1` (title) 블록은 병합 제외
- `type == "list"` 블록은 병합 제외

**변경 파일:**

| 파일 | 변경 내용 |
|------|-----------|
| `src/models/paper.py` | `Paragraph`에 `bboxes: Optional[List[dict]]` 필드 추가 |
| `src/parser/paragraph_builder.py` | `_should_merge()` + `merge_broken_paragraphs()` 구현 |
| `src/parser/mineru_parser.py` | `build()` → `merge_broken_paragraphs()` 호출로 변경 |
| `src/app.py` | 멀티 bbox 하이라이트: `highlightMultiBbox(bboxes)` JS, 다중 영역 rect 생성 |

**데이터 구조:**
- 병합된 문단: `bboxes = [{"bbox": [...], "page": int}, ...]`
- `page`, `bbox`는 첫 번째 블록 기준 (하위 호환)

## 핵심 기술 포인트

### bbox 좌표 계산
```javascript
// MinerU bbox: 정규화×1000 형식
// SVG viewBox 기준으로 변환
const x = (bbox[0] / 1000) * imgWidth;
const y = (bbox[1] / 1000) * imgHeight;
```

### Gradio JavaScript 실행
```python
# gr.Blocks(head=...) 로 <script> 주입 (Gradio sanitization 우회)
HIGHLIGHT_HEAD = """<script>
window.highlightMultiBbox = function(bboxes) { ... };
window.clearHighlight = function() { ... };
</script>"""

gr.Blocks(head=HIGHLIGHT_HEAD)
```

### SVG 오버레이
```html
<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">
```
- viewBox로 이미지 축소와 무관하게 좌표 동기화

## 알려진 이슈

### 1. MinerU MPS 크래시
- Mac MPS에서 간헐적 크래시 (NSRangeException)
- **우회**: `output/` 폴더에 캐시된 결과 재사용

### 2. 문장 단위 하이라이트 불가
- MinerU는 블록(문단) 단위 bbox만 제공
- character-level bbox 없음
- 정확한 문장 단위는 OCR 기반 솔루션 필요

### 3. 번역 누락 가능성
- 개발일지에 "빠진 paragraph 해결" 작업 남아있음
- 배치 번역 결과 개수 불일치 시 확인 필요

## 다음 작업
- [ ] UI/UX 개선
- [ ] 문장 단위 하이라이트 (OCR 기반 솔루션 검토)
- [ ] 크로스 페이지 병합 엣지케이스 테스트

## AI Agent 워크플로우
- **Claude Code**: 계획/프롬프팅 전용 (코드 수정 금지!)
- **Codex**: 코드 구현/실행
- 워크플로우: `CODEX_PROMPT.md` 작성 → Codex 실행 → `codex-result.md` 확인

## 실행 방법
```bash
# 가상환경 활성화
source .venv/bin/activate

# Gradio 앱 실행
python -m src.app

# CLI 사용
python -m src.cli <pdf> -o <output.md> -l ko
```

## 환경 변수
- `OPENAI_API_KEY`: .env 파일에 설정

## 테스트 PDF
- `test.pdf`: 프로젝트 루트에 있음
- 파싱 결과: `output/test/hybrid_auto/test_content_list.json`
