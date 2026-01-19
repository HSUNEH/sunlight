양방향 하이라이트 - PDF hover → 번역본 하이라이트

## 현재 상태
- 번역본 hover → PDF 하이라이트 ✅
- PDF hover → 번역본 하이라이트 ❌ (추가 필요)

## 구현 방법
PDF 이미지에서 마우스 위치를 감지하고, 해당 위치가 어떤 bbox에 해당하는지 찾아서 번역본을 하이라이트

## 수정 파일
`src/app.py`

## 수정 내용

### 1. PDF 페이지에 클릭 영역 추가 (generate_html 함수)

각 문단의 bbox 영역을 클릭 가능한 rect로 추가:

```python
# 페이지별 이미지 HTML 생성 부분 수정
pdf_pages_html = ""
for i, img in enumerate(pdf_images):
    # 해당 페이지의 bbox들을 SVG rect로 추가 (투명, hover 감지용)
    bbox_rects = ""
    for p in pairs:
        if p["page"] == i:
            bbox = p["bbox"]
            bbox_rects += f'''
            <rect class="bbox-area" data-id="{p["id"]}"
                  x="{(bbox[0] / 1000) * img["width"]}"
                  y="{(bbox[1] / 1000) * img["height"]}"
                  width="{((bbox[2] - bbox[0]) / 1000) * img["width"]}"
                  height="{((bbox[3] - bbox[1]) / 1000) * img["height"]}"
                  onmouseenter="highlightTranslation({p["id"]})"
                  onmouseleave="clearTranslationHighlight()"
                  style="fill: transparent; cursor: pointer; pointer-events: all;" />
            '''

    pdf_pages_html += f\'\'\'
    <div class="pdf-page" data-page="{i}">
        <img src="data:image/png;base64,{img["base64"]}" />
        <svg class="pdf-overlay" data-page="{i}"
             viewBox="0 0 {img["width"]} {img["height"]}"
             preserveAspectRatio="none"
             style="pointer-events: none;">
        </svg>
        <svg class="pdf-clickable" data-page="{i}"
             viewBox="0 0 {img["width"]} {img["height"]}"
             preserveAspectRatio="none"
             style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
            {bbox_rects}
        </svg>
    </div>
    \'\'\'
```

주의: generate_html 함수에 pairs 파라미터 추가 필요

### 2. JavaScript 함수 추가 (HIGHLIGHT_JS)

```javascript
window.highlightTranslation = function(id) {
    // 기존 번역본 하이라이트 제거
    document.querySelectorAll('.para.highlight').forEach(el => el.classList.remove('highlight'));

    // 해당 번역본 하이라이트
    var para = document.querySelector('.para[data-id="' + id + '"]');
    if (para) {
        para.classList.add('highlight');
        para.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
};

window.clearTranslationHighlight = function() {
    document.querySelectorAll('.para.highlight').forEach(el => el.classList.remove('highlight'));
};
```

### 3. CSS 추가

```css
.para.highlight { background: #fff3cd; }
```

## 테스트
```bash
source .venv/bin/activate && python -m src.app
```

## 확인
1. test.pdf 업로드 → 번역
2. PDF에서 텍스트 영역에 마우스 hover → 오른쪽 번역본 하이라이트 확인
3. 번역본 hover → PDF 하이라이트 확인 (기존 기능 유지)
