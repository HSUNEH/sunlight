"""ParagraphBuilder tests including list_items handling."""

from src.parser.paragraph_builder import ParagraphBuilder


class TestExtractText:
    """ParagraphBuilder._extract_text static method tests."""

    def test_text_field(self):
        """text 필드가 있는 블록 -> 정상 추출."""
        block = {"text": "Hello world"}
        assert ParagraphBuilder._extract_text(block) == "Hello world"

    def test_content_field(self):
        """content 필드가 있는 블록 -> 정상 추출."""
        block = {"content": "Some content"}
        assert ParagraphBuilder._extract_text(block) == "Some content"

    def test_list_items_field(self):
        """list_items 필드가 있는 블록 -> join으로 합쳐짐."""
        block = {"list_items": ["item1", "item2", "item3"]}
        assert ParagraphBuilder._extract_text(block) == "item1\nitem2\nitem3"

    def test_text_takes_priority_over_list_items(self):
        """text + list_items 둘 다 있는 블록 -> text 우선."""
        block = {"text": "Primary text", "list_items": ["a", "b"]}
        assert ParagraphBuilder._extract_text(block) == "Primary text"

    def test_empty_block(self):
        """빈 블록 -> 빈 문자열 반환."""
        block = {}
        assert ParagraphBuilder._extract_text(block) == ""

    def test_empty_text_and_empty_list_items(self):
        """빈 text + 빈 list_items -> 빈 문자열 반환."""
        block = {"text": "", "list_items": []}
        assert ParagraphBuilder._extract_text(block) == ""

    def test_content_field_when_text_is_empty(self):
        """text가 빈 문자열이면 content로 fallback."""
        block = {"text": "", "content": "Fallback content"}
        assert ParagraphBuilder._extract_text(block) == "Fallback content"


class TestBuild:
    """ParagraphBuilder.build method tests."""

    def setup_method(self):
        self.builder = ParagraphBuilder()

    def test_build_with_text_blocks(self):
        """text 필드가 있는 블록들로 빌드."""
        blocks = [
            {"text": "First paragraph", "page_idx": 0, "bbox": [0, 0, 100, 50]},
            {"text": "Second paragraph", "page_idx": 1, "bbox": [0, 50, 100, 100]},
        ]
        result = self.builder.build(blocks)
        assert len(result) == 2
        assert result[0].text == "First paragraph"
        assert result[1].text == "Second paragraph"

    def test_build_skips_empty_blocks(self):
        """빈 블록은 스킵됨."""
        blocks = [
            {"text": "Real content", "page_idx": 0},
            {},
            {"text": "", "page_idx": 1},
            {"text": "   ", "page_idx": 2},
        ]
        result = self.builder.build(blocks)
        assert len(result) == 1
        assert result[0].text == "Real content"

    def test_build_skips_empty_text_and_empty_list_items(self):
        """빈 text + 빈 list_items -> 스킵됨."""
        blocks = [
            {"text": "", "list_items": [], "page_idx": 0},
        ]
        result = self.builder.build(blocks)
        assert len(result) == 0

    def test_build_preserves_bbox(self):
        """bbox 보존 확인."""
        blocks = [{"text": "Hello", "page_idx": 0, "bbox": [10, 20, 300, 400]}]
        result = self.builder.build(blocks)
        assert len(result) == 1
        assert result[0].bbox == [10, 20, 300, 400]

    def test_build_preserves_page(self):
        """page 보존 확인."""
        blocks = [{"text": "Hello", "page_idx": 5}]
        result = self.builder.build(blocks)
        assert len(result) == 1
        assert result[0].page == 5

    def test_build_default_bbox_and_page(self):
        """bbox, page_idx 없는 블록 -> 기본값."""
        blocks = [{"text": "No metadata"}]
        result = self.builder.build(blocks)
        assert len(result) == 1
        assert result[0].page == 0
        assert result[0].bbox == [0, 0, 0, 0]

    def test_build_with_list_items(self):
        """list_items만 있는 블록도 빌드 가능."""
        blocks = [
            {"list_items": ["alpha", "beta", "gamma"], "page_idx": 3, "bbox": [0, 0, 1, 1]},
        ]
        result = self.builder.build(blocks)
        assert len(result) == 1
        assert "alpha" in result[0].text
        assert "beta" in result[0].text
        assert "gamma" in result[0].text
        assert result[0].page == 3

    def test_build_normalizes_latex(self):
        """빌드 시 LaTeX 정규화 적용 확인."""
        blocks = [{"text": r"\mathrm { x }", "page_idx": 0}]
        result = self.builder.build(blocks)
        assert len(result) == 1
        assert result[0].text == r"\mathrm{x}"
