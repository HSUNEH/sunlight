PDF가 안 보이는 문제 수정

## 문제
- PDF.js가 Gradio HTML sandbox에서 차단됨
- 왼쪽 패널이 비어있음

## 해결 방법
PyMuPDF로 PDF를 이미지로 변환해서 표시

### 1. PyMuPDF 설치
```bash
pip install pymupdf
```

### 2. src/app.py 수정

```python
import fitz  # PyMuPDF 추가

def pdf_to_images(pdf_path, scale=1.5):
    """PDF를 페이지별 base64 이미지로 변환."""
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        images.append({
            "base64": img_base64,
            "width": pix.width,
            "height": pix.height,
            "scale": scale,
        })
    doc.close()
    return images
```

### 3. process_pdf 함수에서 PDF 이미지 변환 추가
```python
pdf_images = pdf_to_images(pdf_file.name, scale=1.5)
return generate_html(pairs, pdf_images)
```

### 4. generate_html 수정
- PDF.js 스크립트 제거
- 페이지별 이미지를 `<img src="data:image/png;base64,...">` 로 표시
- SVG 오버레이는 그대로 유지

## 테스트
```bash
source .venv/bin/activate && python -m src.app
```

## 확인
1. 왼쪽에 PDF 이미지가 보이는지
2. 번역본 hover → PDF에서 하이라이트 되는지
