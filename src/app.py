import asyncio
import base64
import json

import fitz  # PyMuPDF
import gradio as gr
from dotenv import load_dotenv

from src.parser import PaperParser
from src.translator import PaperTranslator

load_dotenv()


def pdf_to_images(pdf_path, scale=1.5):
    """PDF를 페이지별 base64 이미지로 변환."""
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        # scale로 해상도 조절
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


def process_pdf(pdf_file, target_lang, progress=gr.Progress()):
    """PDF 파싱 -> 번역 -> HTML 결과 반환."""
    if pdf_file is None:
        return "<p>PDF 파일을 업로드하세요.</p>"

    progress(0.1, desc="파싱 중...")
    parser = PaperParser()
    parsed = parser.parse(pdf_file.name)

    progress(0.2, desc="번역 중...")
    translator = PaperTranslator()
    translated = asyncio.run(translator.translate_async(parsed, target_lang, batch_size=25))

    progress(0.9, desc="PDF 이미지 변환 중...")
    # PDF를 이미지로 변환
    pdf_images = pdf_to_images(pdf_file.name, scale=1.5)

    progress(0.95, desc="결과 생성 중...")
    # 번역 결과에 bbox, page 정보 포함
    pairs = []
    for i, (orig, trans) in enumerate(zip(parsed.body, translated.body)):
        pairs.append({
            "id": i,
            "original": orig.text,
            "translated": trans.text,
            "bbox": orig.bbox or [0, 0, 0, 0],
            "page": orig.page or 0,
        })

    progress(1.0, desc="완료!")
    return generate_html(pairs, pdf_images)


def generate_html(pairs, pdf_images):
    """PDF 이미지 뷰어 + 번역본 HTML 생성 + 하이라이트 동기화 JS."""

    # 번역본 HTML (bbox, page 데이터 포함)
    translated_html = ""
    for p in pairs:
        bbox_json = json.dumps(p["bbox"])
        translated_html += (
            f'<div class="para" data-id="{p["id"]}" '
            f'data-bbox=\'{bbox_json}\' data-page="{p["page"]}">'
            f'{p["translated"]}</div>'
        )

    # PDF 이미지들을 JSON으로 전달
    pdf_images_json = json.dumps(pdf_images)

    # 페이지별 이미지 HTML 생성
    pdf_pages_html = ""
    for i, img in enumerate(pdf_images):
        pdf_pages_html += f'''
        <div class="pdf-page" data-page="{i}" style="position: relative; margin-bottom: 10px;">
            <img src="data:image/png;base64,{img["base64"]}"
                 style="display: block; width: {img["width"]}px; max-width: 100%;" />
            <svg class="pdf-overlay" data-page="{i}"
                 style="position: absolute; top: 0; left: 0; width: {img["width"]}px; height: {img["height"]}px; pointer-events: none;">
            </svg>
        </div>
        '''

    html = f"""
    <style>
        .container {{ display: flex; gap: 20px; height: 80vh; }}
        .column {{ flex: 1; display: flex; flex-direction: column; min-width: 0; }}
        .column-header {{ font-weight: bold; padding: 10px; background: #f0f0f0; border-radius: 4px 4px 0 0; flex-shrink: 0; }}

        /* PDF 뷰어 */
        .pdf-wrapper {{ flex: 1; overflow-y: auto; overflow-x: auto; border: 1px solid #ddd; border-top: none; background: #525659; padding: 10px; }}
        .pdf-page {{ margin: 0 auto; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
        .pdf-page img {{ max-width: 100%; height: auto; }}
        .highlight-rect {{ fill: rgba(255, 243, 0, 0.4); stroke: #ff9800; stroke-width: 2; }}

        /* 번역본 */
        .translation-wrapper {{ flex: 1; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 4px 4px; }}
        .para {{ padding: 10px; margin: 5px 0; border-radius: 4px; cursor: pointer; transition: background 0.2s; line-height: 1.6; }}
        .para:hover {{ background: #fff3cd; }}
    </style>

    <div class="container">
        <div class="column">
            <div class="column-header">Original PDF</div>
            <div class="pdf-wrapper" id="pdfWrapper">
                {pdf_pages_html}
            </div>
        </div>
        <div class="column">
            <div class="column-header">Translated (KO)</div>
            <div class="translation-wrapper">
                {translated_html}
            </div>
        </div>
    </div>

    <script>
    (function() {{
        const pdfImages = {pdf_images_json};
        let currentHighlight = null;

        function highlightBbox(bbox, pageIdx) {{
            clearHighlight();

            const svg = document.querySelector('.pdf-overlay[data-page="' + pageIdx + '"]');
            if (!svg) return;

            const scale = pdfImages[pageIdx]?.scale || 1.5;

            // bbox: [x_min, y_min, x_max, y_max] (PDF 좌표)
            const x = bbox[0] * scale;
            const y = bbox[1] * scale;
            const width = (bbox[2] - bbox[0]) * scale;
            const height = (bbox[3] - bbox[1]) * scale;

            // SVG rect 생성
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', x);
            rect.setAttribute('y', y);
            rect.setAttribute('width', width);
            rect.setAttribute('height', height);
            rect.setAttribute('class', 'highlight-rect');
            svg.appendChild(rect);

            currentHighlight = {{ svg, rect }};

            // 해당 페이지로 스크롤
            const pageEl = document.querySelector('.pdf-page[data-page="' + pageIdx + '"]');
            if (pageEl) {{
                pageEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            }}
        }}

        function clearHighlight() {{
            if (currentHighlight) {{
                currentHighlight.svg.removeChild(currentHighlight.rect);
                currentHighlight = null;
            }}
        }}

        // 번역본 hover 이벤트
        document.querySelectorAll('.para').forEach(el => {{
            el.addEventListener('mouseenter', () => {{
                const bbox = JSON.parse(el.dataset.bbox);
                const page = parseInt(el.dataset.page);
                highlightBbox(bbox, page);
            }});
            el.addEventListener('mouseleave', () => {{
                clearHighlight();
            }});
        }});
    }})();
    </script>
    """
    return html


def create_app():
    with gr.Blocks(title="논문 번역기") as app:
        gr.Markdown("# 논문 PDF 번역기")
        gr.Markdown(
            "PDF를 업로드하면 파싱 후 번역합니다. "
            "번역된 문단에 마우스를 올리면 원본 PDF에서 해당 위치가 하이라이트됩니다."
        )

        with gr.Row():
            pdf_input = gr.File(label="PDF 업로드", file_types=[".pdf"])
            lang_input = gr.Dropdown(
                choices=["ko", "ja", "zh", "es", "fr", "de"],
                value="ko",
                label="번역 언어",
            )
            submit_btn = gr.Button("번역 시작", variant="primary")

        output_html = gr.HTML(label="결과")

        submit_btn.click(fn=process_pdf, inputs=[pdf_input, lang_input], outputs=[output_html])

    return app


if __name__ == "__main__":
    app = create_app()
    app.launch()
