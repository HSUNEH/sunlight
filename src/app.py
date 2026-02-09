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
        frac = 0.1 + 0.75 * (completed / total)
        progress(frac, desc=f"번역 중... ({completed}/{total} 배치)")

    translated = asyncio.run(
        translator.translate_async(
            parsed, target_lang, batch_size=25, on_batch_done=on_batch_done
        )
    )

    progress(0.9, desc="PDF 이미지 변환 중...")
    pdf_images = pdf_to_images(pdf_file.name, scale=1.5)

    progress(0.95, desc="결과 생성 중...")
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

    total_paras = len(pairs)
    total_pages = len(pdf_images)

    # 번역본 HTML
    translated_html = ""
    for p in pairs:
        bboxes_json = json.dumps(p["bboxes"])
        page_num = p["page"] + 1
        translated_html += (
            f'<div class="para" data-id="{p["id"]}" '
            f'data-bboxes=\'{bboxes_json}\' data-page="{p["page"]}" '
            f"onmouseenter='highlightMultiBbox({bboxes_json}, {p[\"id\"]})' "
            f'onmouseleave="clearHighlight()">'
            f'<span class="para-page-badge">p.{page_num}</span>'
            f'<span class="para-text">{p["translated"]}</span>'
            f'</div>'
        )

    # 페이지별 이미지 HTML
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
        page_label = i + 1
        pdf_pages_html += f'''
        <div class="pdf-page" data-page="{i}">
            <div class="page-number-label">
                <span class="page-num-text">Page {page_label}</span>
                <span class="page-num-total">/ {total_pages}</span>
            </div>
            <div class="pdf-image-container">
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap');

        /* ── Reset & Container ── */
        .viewer-root {{
            font-family: 'Inter', 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif;
            display: flex;
            gap: 0;
            height: 82vh;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 24px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.08);
        }}

        .viewer-panel {{
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
            position: relative;
        }}

        .viewer-panel + .viewer-panel {{
            border-left: 1px solid rgba(0,0,0,0.08);
        }}

        /* ── Panel Headers ── */
        .panel-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 18px;
            background: linear-gradient(135deg, #fafbfc 0%, #f3f4f6 100%);
            border-bottom: 1px solid rgba(0,0,0,0.06);
            flex-shrink: 0;
        }}

        .panel-header-left {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .panel-icon {{
            width: 28px;
            height: 28px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }}

        .panel-icon.pdf {{ background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }}
        .panel-icon.translation {{ background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; }}

        .panel-title {{
            font-size: 13px;
            font-weight: 600;
            color: #1f2937;
            letter-spacing: -0.01em;
        }}

        .panel-subtitle {{
            font-size: 11px;
            color: #9ca3af;
            font-weight: 500;
        }}

        .stat-badge {{
            font-size: 11px;
            color: #6b7280;
            background: white;
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 20px;
            padding: 3px 10px;
            font-weight: 500;
            white-space: nowrap;
        }}

        /* ── PDF Viewer ── */
        .pdf-wrapper {{
            flex: 1;
            overflow-y: auto;
            overflow-x: auto;
            background: #1e1e2e;
            padding: 20px;
            scroll-behavior: smooth;
        }}

        .pdf-wrapper::-webkit-scrollbar {{ width: 8px; }}
        .pdf-wrapper::-webkit-scrollbar-track {{ background: transparent; }}
        .pdf-wrapper::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.15); border-radius: 4px; }}
        .pdf-wrapper::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.25); }}

        .pdf-page {{
            position: relative;
            display: block;
            margin: 0 auto 20px auto;
            background: white;
            border-radius: 4px;
            box-shadow: 0 2px 16px rgba(0,0,0,0.35);
            overflow: hidden;
        }}

        .pdf-page:last-child {{ margin-bottom: 0; }}

        .pdf-image-container {{ position: relative; }}

        .pdf-page img {{
            display: block;
            width: 100%;
            height: auto;
        }}

        .pdf-overlay {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            pointer-events: none;
        }}

        .pdf-clickable {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
        }}

        .highlight-rect {{
            fill: rgba(59, 130, 246, 0.18);
            stroke: #3b82f6;
            stroke-width: 2;
            rx: 3;
            ry: 3;
            animation: highlight-pulse 1.5s ease-in-out infinite;
        }}

        @keyframes highlight-pulse {{
            0%, 100% {{ fill: rgba(59, 130, 246, 0.18); }}
            50% {{ fill: rgba(59, 130, 246, 0.30); }}
        }}

        .page-number-label {{
            background: linear-gradient(135deg, #374151, #1f2937);
            color: #e5e7eb;
            font-size: 11px;
            font-weight: 600;
            padding: 6px 14px;
            text-align: center;
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }}

        .page-num-text {{ color: #f9fafb; }}
        .page-num-total {{ color: #6b7280; font-weight: 400; }}

        /* ── Translation Panel ── */
        .translation-wrapper {{
            flex: 1;
            overflow-y: auto;
            padding: 8px 14px;
            background: #ffffff;
            scroll-behavior: smooth;
        }}

        .translation-wrapper::-webkit-scrollbar {{ width: 6px; }}
        .translation-wrapper::-webkit-scrollbar-track {{ background: transparent; }}
        .translation-wrapper::-webkit-scrollbar-thumb {{ background: rgba(0,0,0,0.10); border-radius: 3px; }}
        .translation-wrapper::-webkit-scrollbar-thumb:hover {{ background: rgba(0,0,0,0.18); }}

        .translation-page-indicator {{
            position: sticky;
            top: 0;
            z-index: 10;
            background: linear-gradient(135deg, #eff6ff, #dbeafe);
            color: #1d4ed8;
            font-size: 11px;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 8px;
            margin-bottom: 8px;
            text-align: center;
            letter-spacing: 0.2px;
            border: 1px solid rgba(59, 130, 246, 0.12);
            backdrop-filter: blur(8px);
        }}

        .para {{
            padding: 12px 14px;
            margin: 4px 0;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            line-height: 1.75;
            font-size: 14px;
            color: #374151;
            border: 1px solid transparent;
            position: relative;
        }}

        .para:hover {{
            background: #f0f7ff;
            border-color: rgba(59,130,246,0.15);
        }}

        .para.highlight {{
            background: linear-gradient(135deg, #eff6ff, #dbeafe);
            border-color: rgba(59,130,246,0.25);
            box-shadow: 0 2px 8px rgba(59,130,246,0.10);
        }}

        .para.highlight .para-page-badge {{
            background: #3b82f6;
            color: white;
            border-color: transparent;
        }}

        .para-page-badge {{
            display: inline-flex;
            align-items: center;
            font-size: 10px;
            color: #9ca3af;
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 5px;
            padding: 1px 7px;
            margin-right: 8px;
            vertical-align: middle;
            font-weight: 600;
            line-height: 1.6;
            letter-spacing: 0.2px;
            transition: all 0.2s ease;
        }}

        .para-text {{
            vertical-align: middle;
        }}

        /* ── Tooltip hint (번역 패널 첫 hover) ── */
        .para::after {{
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            width: 3px;
            height: 100%;
            background: #3b82f6;
            border-radius: 10px 0 0 10px;
            opacity: 0;
            transition: opacity 0.2s ease;
        }}

        .para:hover::after,
        .para.highlight::after {{
            opacity: 1;
        }}
    </style>

    <div class="viewer-root">
        <div class="viewer-panel">
            <div class="panel-header">
                <div class="panel-header-left">
                    <div class="panel-icon pdf">P</div>
                    <div>
                        <div class="panel-title">Original PDF</div>
                        <div class="panel-subtitle">Hover on translation to highlight</div>
                    </div>
                </div>
                <div class="stat-badge">{total_pages} pages</div>
            </div>
            <div class="pdf-wrapper" id="pdfWrapper">
                {pdf_pages_html}
            </div>
        </div>
        <div class="viewer-panel">
            <div class="panel-header">
                <div class="panel-header-left">
                    <div class="panel-icon translation">T</div>
                    <div>
                        <div class="panel-title">Translation</div>
                        <div class="panel-subtitle">Hover on PDF to highlight</div>
                    </div>
                </div>
                <div class="stat-badge">{total_paras} paragraphs</div>
            </div>
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
<style>
    /* Gradio container overrides */
    .gradio-container {
        max-width: 100% !important;
        padding: 16px 24px !important;
    }
    footer { display: none !important; }
</style>
<script>
window.highlightMultiBbox = function(bboxes, paraId) {
    window.clearHighlight();
    window.currentHighlights = [];

    if (!bboxes || !bboxes.length) return;

    // 번역 패널에서도 active 표시
    if (paraId !== undefined) {
        var para = document.querySelector('.para[data-id="' + paraId + '"]');
        if (para) para.classList.add('highlight');
    }

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

    var firstPage = bboxes[0].page;
    var pageEl = document.querySelector('.pdf-page[data-page="' + firstPage + '"]');
    if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
};

window.clearHighlight = function() {
    // 번역 패널 하이라이트 제거
    document.querySelectorAll('.para.highlight').forEach(function(el) {
        el.classList.remove('highlight');
    });

    if (window.currentHighlights) {
        for (var i = 0; i < window.currentHighlights.length; i++) {
            var h = window.currentHighlights[i];
            if (h.rect.parentNode === h.svg) {
                h.svg.removeChild(h.rect);
            }
        }
        window.currentHighlights = [];
    }
    if (window.currentHighlight) {
        if (window.currentHighlight.rect.parentNode === window.currentHighlight.svg) {
            window.currentHighlight.svg.removeChild(window.currentHighlight.rect);
        }
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


CUSTOM_CSS = """
.app-header {
    text-align: center;
    padding: 8px 0 4px 0;
}
.app-header h1 {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #111827;
    margin: 0;
    letter-spacing: -0.02em;
}
.app-header p {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    color: #6b7280;
    margin: 6px 0 0 0;
    line-height: 1.5;
}
"""


def create_app():
    with gr.Blocks(
        title="Sunlight - Paper Translator",
        head=HIGHLIGHT_HEAD,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(
            primary_hue=gr.themes.colors.blue,
            neutral_hue=gr.themes.colors.gray,
            font=gr.themes.GoogleFont("Inter"),
        ),
    ) as app:
        gr.HTML(
            '<div class="app-header">'
            "<h1>Sunlight</h1>"
            "<p>PDF 논문을 업로드하면 자동으로 파싱하고 번역합니다. "
            "번역문과 원본 PDF가 양방향으로 하이라이트 연동됩니다.</p>"
            "</div>"
        )

        with gr.Row(equal_height=True):
            pdf_input = gr.File(
                label="PDF 업로드",
                file_types=[".pdf"],
                scale=3,
            )
            lang_input = gr.Dropdown(
                choices=["ko", "ja", "zh", "es", "fr", "de"],
                value="ko",
                label="Target Language",
                scale=1,
            )
            submit_btn = gr.Button(
                "Translate",
                variant="primary",
                scale=1,
                size="lg",
            )

        output_html = gr.HTML(label="결과")

        submit_btn.click(fn=process_pdf, inputs=[pdf_input, lang_input], outputs=[output_html])

    return app


if __name__ == "__main__":
    app = create_app()
    app.launch()
