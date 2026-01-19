from pathlib import Path

from src.parser import PaperParser


def test_parser_classifies_blocks(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    blocks = [
        {"type": "title", "content": "Intro", "page_idx": 0},
        {"type": "text", "content": "First sentence.", "page_idx": 0},
        {"type": "list", "content": "Item one.", "page_idx": 0},
        {"type": "table", "html": "<table></table>", "page_idx": 1},
        {"type": "image", "img_path": "images/fig1.png", "page_idx": 1},
        {"type": "equation", "latex": "E = mc^2", "page_idx": 2},
        {"type": "header", "content": "Header", "page_idx": 0},
    ]

    parser = PaperParser()
    parser._run_mineru = lambda _: iter(blocks)

    result = parser.parse(pdf_path)

    assert len(result.body) == 3
    assert result.body[0].text == "Intro"
    assert result.body[1].text == "First sentence."
    assert result.body[2].text == "Item one."
    assert len(result.tables) == 1
    assert result.tables[0].html == "<table></table>"
    assert len(result.figures) == 1
    assert result.figures[0].path == "images/fig1.png"
    assert result.equations == ["E = mc^2"]
    assert len(result.metadata.get("raw", [])) == 1
