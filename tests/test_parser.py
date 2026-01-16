from pathlib import Path

import pytest

from src.parser import PaperParser


@pytest.mark.xfail(reason="MinerU integration not implemented")
def test_parser_raises_when_unimplemented(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    parser = PaperParser()
    with pytest.raises(NotImplementedError):
        parser.parse(pdf_path)
