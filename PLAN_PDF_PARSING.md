# 논문 PDF 파싱/전처리 계획

## 문제 정의

현재 문제점:
1. **테이블 혼입** - 테이블이 본문 번역에 포함됨
2. **메타데이터 혼입** - 주석, 저자 이름, 소속 등이 본문에 섞임
3. **문단 구분 실패** - 단락 경계가 제대로 인식 안됨

## 추천 솔루션: MinerU

### 선택 이유

| 도구 | 장점 | 단점 |
|------|------|------|
| **MinerU** | LLM-ready 출력, 테이블→HTML, 수식→LaTeX, 109언어 OCR, 활발한 개발 | 설치 복잡 |
| GROBID | TEI-XML 구조화, 생산환경 검증, 68개 라벨 분류 | 서버 실행 필요, 출력이 XML |
| Marker | 빠름(Nougat 4배), 다국어 지원 | 상업용 라이선스 필요 |
| Nougat | arXiv 논문에 최적화, 수식 처리 우수 | arXiv 외 문서 정확도 낮음 |

**MinerU 추천 이유:**
- 레이아웃 감지 → 영역별 처리 → 읽기 순서 정렬 파이프라인
- 헤더/푸터/페이지번호/각주 자동 제거
- 테이블을 HTML로, 수식을 LaTeX로 분리 추출
- Markdown/JSON 출력으로 번역 파이프라인 연동 용이

## 구현 계획

### Phase 1: 환경 설정 (Mac Apple Silicon)

```bash
pip install mineru
```

**Mac MPS 설정:**
```json
// ~/.mineru/config.json
{
  "device-mode": "mps"
}
```

```bash
# MPS fallback 활성화 (호환성 이슈 대비)
export PYTORCH_ENABLE_MPS_FALLBACK=1
```

- Python 3.10-3.13 필요
- Mac MPS 지원됨 (일부 호환성 이슈 가능, CPU fallback 있음)
- M1/M2/M3 칩에서 CPU 대비 빠른 처리 기대

### Phase 2: 파싱 파이프라인 구조

```
PDF 입력
    ↓
[MinerU 처리]
    ├── Layout Detection (DocLayout-YOLO)
    │   ├── 본문 영역
    │   ├── 테이블 영역
    │   ├── 수식 영역
    │   ├── 그림 영역
    │   └── 메타데이터 영역 (저자, 소속, 각주 등)
    ↓
[영역별 추출]
    ├── 본문 → Markdown (문단 구분 유지)
    ├── 테이블 → HTML/JSON (별도 저장)
    ├── 수식 → LaTeX (인라인 vs 블록 구분)
    ├── 그림 → 이미지 파일 + 캡션
    └── 메타데이터 → JSON (번역 제외)
    ↓
[출력 구조]
    ├── content.md (본문만)
    ├── tables/ (테이블들)
    ├── figures/ (그림들)
    ├── equations.json (수식들)
    └── metadata.json (저자, 참고문헌 등)
```

### Phase 3: 핵심 모듈 구현

#### 3.1 PDF 파서 모듈
```python
# parser.py
class PaperParser:
    def parse(self, pdf_path: str) -> ParsedPaper
    def extract_body(self) -> list[Paragraph]
    def extract_tables(self) -> list[Table]
    def extract_figures(self) -> list[Figure]
    def extract_metadata(self) -> Metadata
```

#### 3.2 콘텐츠 분류기
```python
# classifier.py
class ContentClassifier:
    def is_body_text(self, block) -> bool
    def is_table(self, block) -> bool
    def is_footnote(self, block) -> bool
    def is_header_footer(self, block) -> bool
```

#### 3.3 문단 재구성기
```python
# paragraph.py
class ParagraphBuilder:
    def merge_broken_paragraphs(self, blocks) -> list[Paragraph]
    def detect_paragraph_boundaries(self, lines) -> list[int]
```

### Phase 4: 번역 연동

```
[번역 대상]
- content.md 의 본문 텍스트만

[번역 제외]
- 테이블 (원본 유지)
- 저자명, 소속, 이메일
- 참고문헌 목록
- 각주 번호
- 수식 (LaTeX 그대로 유지)
- 그림 캡션
```

## 파일 구조

```
sunlight/
├── src/
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── mineru_parser.py    # MinerU 래퍼
│   │   ├── content_classifier.py
│   │   └── paragraph_builder.py
│   ├── models/
│   │   ├── paper.py            # ParsedPaper, Paragraph, Table 등
│   │   └── metadata.py
│   └── utils/
│       └── pdf_utils.py
├── tests/
│   └── test_parser.py
├── requirements.txt
└── Agent.md
```

## VLM vs OpenAI API 비교

| 방식 | 장점 | 단점 |
|------|------|------|
| **MinerU (VLM 기반)** | 로컬 실행, 비용 없음, 구조 추출 우수 | GPU 필요, 초기 설정 복잡 |
| **OpenAI API** | 설정 간단, 높은 이해도 | 비용 발생, 이미지 토큰 비쌈 |

**추천:** MinerU로 구조 추출 → OpenAI로 번역 (하이브리드)

## 검증 방법

1. **테스트 논문 3종 준비**
   - 단순 구조 (텍스트 위주)
   - 복잡 구조 (테이블 + 수식 다수)
   - 2컬럼 레이아웃

2. **검증 항목**
   - [ ] 테이블이 본문에서 분리되었는가
   - [ ] 저자/소속이 메타데이터로 분류되었는가
   - [ ] 문단 경계가 올바르게 유지되었는가
   - [ ] 수식이 LaTeX로 추출되었는가
   - [ ] 읽기 순서가 올바른가 (2컬럼 처리)

## MinerU 출력 스키마

### 출력 파일 구조
```
output/
├── {filename}.md              # 메인 Markdown 출력
├── {filename}_model.json      # 레이아웃 감지 결과
├── {filename}_middle.json     # 중간 구조화 데이터
├── {filename}_content_list.json  # 읽기 순서 정렬된 콘텐츠
└── images/                    # 추출된 이미지들
```

### content_list.json 스키마 (권장 사용)

```json
[
  {
    "type": "text",           // text | title | table | image | equation | code | list
    "text_level": 0,          // 0=본문, 1-N=제목 레벨
    "bbox": [x0, y0, x1, y1], // 좌표 (0-1000 정규화)
    "page_idx": 0,            // 페이지 번호 (0-indexed)
    "content": "본문 텍스트..."
  },
  {
    "type": "title",
    "text_level": 1,
    "content": "Introduction"
  },
  {
    "type": "table",
    "html": "<table>...</table>",  // HTML 형식 테이블
    "bbox": [100, 200, 500, 400],
    "page_idx": 1
  },
  {
    "type": "equation",
    "latex": "E = mc^2",           // LaTeX 수식
    "bbox": [150, 300, 450, 350]
  },
  {
    "type": "image",
    "img_path": "images/fig1.png",
    "bbox": [50, 100, 550, 400]
  }
]
```

### Block Type 분류 (19종)

| type | 설명 | 번역 대상 |
|------|------|----------|
| `text` | 본문 텍스트 | ✅ |
| `title` | 제목/섹션 헤더 | ✅ |
| `table` | 테이블 (HTML) | ❌ |
| `image` | 이미지 | ❌ |
| `equation` | 수식 (LaTeX) | ❌ |
| `code` | 코드 블록 | ❌ |
| `list` | 리스트 | ✅ |
| `header` | 페이지 헤더 | ❌ (자동 제외) |
| `footer` | 페이지 푸터 | ❌ (자동 제외) |
| `page_number` | 페이지 번호 | ❌ (자동 제외) |
| `aside_text` | 사이드 텍스트 | ❌ |
| `page_footnote` | 각주 | ❌ |

### middle.json 구조 (상세 분석용)

```json
{
  "pdf_info": [
    {
      "page_idx": 0,
      "para_blocks": [
        {
          "type": "text",
          "lines": [
            {
              "bbox": [x0, y0, x1, y1],
              "spans": [
                {
                  "type": "text",      // text | inline_equation
                  "content": "텍스트",
                  "bbox": [...]
                }
              ]
            }
          ]
        }
      ],
      "images": [...],
      "tables": [...],
      "discarded_blocks": [...]  // header, footer, page_number
    }
  ],
  "_backend": "pipeline",  // 또는 "vlm"
  "_parse_type": "txt",    // txt | ocr
  "_version_name": "2.7.1"
}
```

### 파서 구현 시 활용 방법

```python
# content_list.json 파싱 예시
def parse_content_list(content_list: list) -> ParsedPaper:
    body_blocks = []
    tables = []
    figures = []
    equations = []

    for block in content_list:
        block_type = block.get("type")

        if block_type in ("text", "title", "list"):
            # 번역 대상
            body_blocks.append({
                "type": block_type,
                "content": block.get("content", ""),
                "level": block.get("text_level", 0),
                "page": block.get("page_idx", 0),
                "bbox": block.get("bbox")
            })
        elif block_type == "table":
            tables.append({
                "html": block.get("html", ""),
                "page": block.get("page_idx", 0)
            })
        elif block_type == "image":
            figures.append({
                "path": block.get("img_path", ""),
                "page": block.get("page_idx", 0)
            })
        elif block_type == "equation":
            equations.append({
                "latex": block.get("latex", ""),
                "page": block.get("page_idx", 0)
            })
        # header, footer, page_number 등은 자동으로 discarded

    return ParsedPaper(body=body_blocks, tables=tables, ...)
```

## 다음 단계

1. MinerU 설치 및 기본 테스트
2. 샘플 논문으로 파싱 결과 확인
3. 필요시 후처리 로직 추가
4. 번역 파이프라인 연동

## 참고 자료

- [MinerU GitHub](https://github.com/opendatalab/MinerU)
- [GROBID Documentation](https://grobid.readthedocs.io/en/latest/)
- [Marker GitHub](https://github.com/datalab-to/marker)
- [Nougat (Meta)](https://github.com/facebookresearch/nougat)
- [PDF Parsing 비교 연구](https://arxiv.org/abs/2410.09871)
