# Handoff Document (2026-02-09)

## 프로젝트 개요
**sunlight** - arXiv 논문 번역기 + 원본-번역 하이라이트 동기화

## 기술 스택
- **PDF 파싱**: MinerU v2.7.6 (pipeline 백엔드, GPU 불필요)
- **번역**: OpenAI API (gpt-4o-mini)
- **프론트엔드**: Gradio 6.5
- **PDF 렌더링**: PyMuPDF (fitz)

## 프로젝트 구조
```
sunlight/
├── src/
│   ├── app.py              # Gradio 웹 앱 (메인) - arXiv URL 입력
│   ├── cli.py              # CLI 파이프라인
│   ├── parser/
│   │   ├── mineru_parser.py    # MinerU CLI 래퍼 (pipeline 백엔드)
│   │   ├── paragraph_builder.py # 블록 → Paragraph 변환 + 병합
│   │   └── content_classifier.py # 본문/메타/사사 분류
│   ├── translator/
│   │   └── openai_translator.py # 배치 번역 + async
│   └── models/
│       └── paper.py        # Paragraph, ParsedPaper 모델
├── tests/
├── output/                 # MinerU 파싱 결과 캐시
├── AGENTS.md              # AI 에이전트 역할 정의
└── 개발일지.md
```

## 완료된 기능

### 1. arXiv URL 입력
- PDF 업로드 대신 arXiv URL만 입력하면 자동으로 PDF 다운로드
- 지원 형식: `arxiv.org/abs/`, `arxiv.org/pdf/`, `arxiv.org/html/` + 버전(`v2` 등)
- CLI에서도 URL 직접 입력 가능: `python -m src.cli https://arxiv.org/abs/2301.12345`

### 2. PDF 파싱 파이프라인
- MinerU `pipeline` 백엔드로 PDF → JSON (content_list.json)
- bbox 좌표 보존 (`[x_min, y_min, x_max, y_max]`, 정규화×1000)
- 기존 `hybrid-auto-engine` 캐시도 자동 감지하여 재사용

### 3. 번역
- 배치 번역 (25개씩)
- AsyncOpenAI 병렬 처리 (semaphore=3)
- 실패 시 개별 비동기 번역 fallback
- Target Language: 한국어 고정

### 4. Gradio 웹 앱
- arXiv URL 입력 + Translate 버튼만 있는 단순한 UI
- 좌우 분할: PDF 이미지 | 번역본
- **양방향 하이라이트** (hover 시 강조, 자동 스크롤 없음):
  - 번역본 hover → PDF 하이라이트
  - PDF hover → 번역본 하이라이트
- JavaScript: `gr.Blocks(head=...)` 로 `<script>` 주입

### 5. 끊어진 문단 병합 (Cross-Column / Cross-Page Merging)
MinerU가 2칼럼 레이아웃이나 페이지 넘김에서 하나의 문장을 별도 블록으로 분리하는 문제 해결.

**병합 판단 로직:**
- 현재 블록 텍스트가 `.!?:;`로 끝나지 않으면 → 다음 블록과 병합
- 다음 블록이 소문자로 시작하면 → 문장 연속으로 판단하여 강제 병합
- 컬럼 변경 시 다음 블록이 현재보다 훨씬 위에 있으면 → 별개 문단 (각주 오병합 방지)
- `text_level == 1` (title) / `type == "list"` 블록은 병합 제외

**데이터 구조:**
- 병합된 문단: `bboxes = [{"bbox": [...], "page": int}, ...]`
- `page`, `bbox`는 첫 번째 블록 기준 (하위 호환)

### 6. 논문 메타 정보 필터링
번역 대상에서 제외되는 블록:
- **저자/소속**: 논문 타이틀 ~ 첫 번째 섹션 제목 사이 블록 (Abstract 제외)
- **사사 표기**: "This work was supported by...", "The authors acknowledge..." 등
- **References 이후**: 참고문헌 섹션 전체

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

### 1. MinerU 의존성
- `mineru[full]` 설치 후 추가로 필요: `doclayout-yolo`, `ultralytics`, `accelerate`, `ftfy`, `shapely`, `pyclipper`, `omegaconf`
- `torch>=2.7` 권장 (2.10에서 `doclayout-yolo` weight 로딩 에러)
- Mac MPS에서 간헐적 크래시 → `pipeline` 백엔드가 `mps` 실패 시 자동으로 `cpu` fallback

### 2. 문장 단위 하이라이트 불가
- MinerU는 블록(문단) 단위 bbox만 제공
- character-level bbox 없음
- 정확한 문장 단위는 OCR 기반 솔루션 필요

### 3. 번역 배치 불일치
- 배치 번역 결과 개수 불일치 시 개별 번역으로 fallback
- 로그: `Batch count mismatch` → 정상 동작 (자동 복구)

## 다음 작업
- [x] ~~UI/UX 개선~~ (Sunlight 테마 적용 완료)
- [x] ~~arXiv URL 입력 지원~~
- [x] ~~저자/소속/사사 표기 번역 제외~~
- [x] ~~MinerU pipeline 백엔드 전환~~
- [x] ~~하이라이트 시 자동 스크롤 제거~~
- [ ] 문장 단위 하이라이트 (OCR 기반 솔루션 검토)
- [ ] 로딩 progress bar 표시 개선

## 실행 방법
```bash
# Gradio 앱 실행
python -m src.app

# CLI 사용 (arXiv URL 또는 PDF 경로)
python -m src.cli https://arxiv.org/abs/2504.18157 -o translated.md
python -m src.cli paper.pdf -o translated.md
```

## 환경 변수
- `OPENAI_API_KEY`: .env 파일에 설정

## 테스트
- 테스트 논문: `https://arxiv.org/abs/2504.18157`
- 파싱 결과 캐시: `output/<paper_id>/auto/<paper_id>_content_list.json`
