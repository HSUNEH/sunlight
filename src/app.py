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

    progress(0.05, desc="파싱 중...")
    parser = PaperParser()
    parsed = parser.parse(pdf_file.name)

    progress(0.1, desc="번역 준비 중...")
    translator = PaperTranslator()

    def on_batch_done(completed, total):
        # 번역 구간: 0.1 ~ 0.85
        frac = 0.1 + 0.75 * (completed / total)
        progress(frac, desc=f"번역 중... ({completed}/{total} 배치)")

    translated = asyncio.run(
        translator.translate_async(
            parsed, target_lang, batch_size=25, on_batch_done=on_batch_done
        )
    )

    progress(0.9, desc="PDF 이미지 변환 중...")
    # PDF를 이미지로 변환
    pdf_images = pdf_to_images(pdf_file.name, scale=1.5)

    progress(0.95, desc="결과 생성 중...")
    # 번역 결과에 bbox, page 정보 포함
    pairs = []
    for i, (orig, trans) in enumerate(zip(parsed.body, translated.body)):
        bboxes = orig.bboxes or [{"bbox": orig.bbox or [0, 0, 0, 0], "page": orig.page or 0}]
        pairs.append({
            "id": i,
            "original": orig.text,
            "translated": trans.text,
            "bbox": orig.bbox or [0, 0, 0, 0],
            "page": orig.page or 0,
            "bboxes": bboxes,
        })

    progress(1.0, desc="완료!")
    return generate_html(pairs, pdf_images)


def generate_html(pairs, pdf_images):
    """PDF 이미지 뷰어 + 번역본 HTML 생성."""

    # 번역본 HTML (bbox, page 데이터 포함)
    translated_html = ""
    for p in pairs:
        bboxes_json = json.dumps(p["bboxes"])
        page_num = p["page"] + 1  # 1-based display
        translated_html += (
            f'<div class="para" data-id="{p["id"]}" '
            f'data-bboxes=\'{bboxes_json}\' data-page="{p["page"]}" '
            f"onmouseenter='highlightMultiBbox({bboxes_json})' "
            f'onmouseleave="clearHighlight()">'
            f'<span class="para-page-badge">p.{page_num}</span>'
            f'{p["translated"]}</div>'
        )

    # 페이지별 이미지 HTML 생성
    pdf_pages_html = ""
    for i, img in enumerate(pdf_images):
        bbox_rects = ""
        for p in pairs:
            for region in p["bboxes"]:
                if region["page"] != i:
                    continue
                bbox = region["bbox"]
                x = (bbox[0] / 1000) * img["width"]
                y = (bbox[1] / 1000) * img["height"]
                width = ((bbox[2] - bbox[0]) / 1000) * img["width"]
                height = ((bbox[3] - bbox[1]) / 1000) * img["height"]
                bbox_rects += f'''
            <rect class="bbox-area" data-id="{p["id"]}"
                  x="{x}" y="{y}" width="{width}" height="{height}"
                  onmouseenter="highlightTranslation({p["id"]})"
                  onmouseleave="clearTranslationHighlight()"
                  style="fill: transparent; cursor: pointer; pointer-events: all;" />
            '''
        page_label = i + 1  # 1-based display
        pdf_pages_html += f'''
        <div class="pdf-page" data-page="{i}">
            <div class="page-number-label">Page {page_label}</div>
            <div class="pdf-image-container" style="position: relative;">
                <img src="data:image/png;base64,{img["base64"]}" />
                <svg class="pdf-overlay" data-page="{i}"
                     viewBox="0 0 {img["width"]} {img["height"]}"
                     preserveAspectRatio="none">
                </svg>
                <svg class="pdf-clickable" data-page="{i}"
                     viewBox="0 0 {img["width"]} {img["height"]}"
                     preserveAspectRatio="none">
                    {bbox_rects}
                </svg>
            </div>
        </div>
        '''

    # KaTeX CDN for LaTeX rendering
    katex_cdn = """
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
            onload="renderMathInElement(document.body, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false}
                ],
                throwOnError: false
            });"></script>
    """

    html = katex_cdn + f"""
    <style>
        .container {{ display: flex; gap: 20px; height: 80vh; }}
        .column {{ flex: 1; display: flex; flex-direction: column; min-width: 0; }}
        .column-header {{ font-weight: bold; padding: 10px; background: #f0f0f0; border-radius: 4px 4px 0 0; flex-shrink: 0; }}

        /* PDF 뷰어 */
        .pdf-wrapper {{ flex: 1; overflow-y: auto; overflow-x: auto; border: 1px solid #ddd; border-top: none; background: #525659; padding: 10px; }}
        .pdf-page {{ position: relative; display: inline-block; margin: 0 auto; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
        .pdf-image-container {{ position: relative; }}
        .pdf-page img {{ display: block; width: 100%; height: auto; }}
        .pdf-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }}
        .pdf-clickable {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}
        .highlight-rect {{ fill: rgba(255, 243, 0, 0.4); stroke: #ff9800; stroke-width: 2; }}

        /* 번역본 */
        .translation-wrapper {{ flex: 1; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 4px 4px; }}
        .para {{ padding: 10px; margin: 5px 0; border-radius: 4px; cursor: pointer; transition: background 0.2s; line-height: 1.6; }}
        .para:hover {{ background: #fff3cd; }}
        .para.highlight {{ background: #fff3cd; }}

        /* 페이지 번호 라벨 (PDF 뷰어) */
        .page-number-label {{ background: rgba(0,0,0,0.6); color: #fff; font-size: 12px; font-weight: 600; padding: 3px 10px; text-align: center; letter-spacing: 0.5px; }}

        /* 번역본 페이지 배지 */
        .para-page-badge {{ display: inline-block; font-size: 10px; color: #888; background: #f0f0f0; border-radius: 3px; padding: 1px 5px; margin-right: 6px; vertical-align: middle; font-weight: 600; line-height: 1.4; }}

        /* 번역본 현재 페이지 표시 */
        .translation-page-indicator {{ position: sticky; top: 0; z-index: 10; background: #e8f4fd; color: #1a73e8; font-size: 12px; font-weight: 600; padding: 4px 10px; border-bottom: 1px solid #c2dff5; text-align: center; }}
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
            <div class="translation-wrapper" id="translationWrapper">
                <div class="translation-page-indicator" id="translationPageIndicator">Page 1</div>
                {translated_html}
            </div>
        </div>
    </div>
    """
    return html


# -- JS injected via Blocks(head=...) so it survives Gradio's HTML sanitization --
HIGHLIGHT_HEAD = """
<script>
window.highlightMultiBbox = function(bboxes) {
    window.clearHighlight();
    window.currentHighlights = [];

    if (!bboxes || !bboxes.length) return;

    for (var i = 0; i < bboxes.length; i++) {
        var region = bboxes[i];
        var bbox = region.bbox;
        var pageIdx = region.page;

        var svg = document.querySelector('.pdf-overlay[data-page="' + pageIdx + '"]');
        if (!svg) continue;

        var viewBox = svg.viewBox.baseVal;
        var svgW = viewBox.width;
        var svgH = viewBox.height;

        var x = (bbox[0] / 1000) * svgW;
        var y = (bbox[1] / 1000) * svgH;
        var width = ((bbox[2] - bbox[0]) / 1000) * svgW;
        var height = ((bbox[3] - bbox[1]) / 1000) * svgH;

        var rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', x);
        rect.setAttribute('y', y);
        rect.setAttribute('width', width);
        rect.setAttribute('height', height);
        rect.setAttribute('class', 'highlight-rect');
        svg.appendChild(rect);

        window.currentHighlights.push({ svg: svg, rect: rect });
    }

    // 첫 번째 영역으로 스크롤
    var firstPage = bboxes[0].page;
    var pageEl = document.querySelector('.pdf-page[data-page="' + firstPage + '"]');
    if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
};

window.clearHighlight = function() {
    if (window.currentHighlights) {
        for (var i = 0; i < window.currentHighlights.length; i++) {
            var h = window.currentHighlights[i];
            h.svg.removeChild(h.rect);
        }
        window.currentHighlights = [];
    }
    // 하위 호환: 단일 하이라이트도 정리
    if (window.currentHighlight) {
        window.currentHighlight.svg.removeChild(window.currentHighlight.rect);
        window.currentHighlight = null;
    }
};

window.highlightTranslation = function(id) {
    window.clearTranslationHighlight();
    var para = document.querySelector('.para[data-id="' + id + '"]');
    if (para) {
        para.classList.add('highlight');
        para.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
};

window.clearTranslationHighlight = function() {
    document.querySelectorAll('.para.highlight').forEach(function(el) {
        el.classList.remove('highlight');
    });
};

window.updateTranslationPageIndicator = function() {
    var wrapper = document.getElementById('translationWrapper');
    var indicator = document.getElementById('translationPageIndicator');
    if (!wrapper || !indicator) return;

    var paras = wrapper.querySelectorAll('.para[data-page]');
    var currentPage = 0;
    var wrapperTop = wrapper.scrollTop + wrapper.offsetTop;

    paras.forEach(function(para) {
        if (para.offsetTop <= wrapperTop + 60) {
            currentPage = parseInt(para.getAttribute('data-page')) || 0;
        }
    });

    indicator.textContent = 'Page ' + (currentPage + 1);
};

// DOM 변경 감지하여 번역 결과가 로드되면 스크롤 옵저버 설정
var _scrollBound = false;
new MutationObserver(function() {
    if (_scrollBound) return;
    var wrapper = document.getElementById('translationWrapper');
    if (wrapper) {
        wrapper.addEventListener('scroll', window.updateTranslationPageIndicator);
        _scrollBound = true;
    }
}).observe(document.body, {childList: true, subtree: true});
</script>
"""


def create_app():
    with gr.Blocks(title="논문 번역기", head=HIGHLIGHT_HEAD) as app:
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
