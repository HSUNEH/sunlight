import pytest
from unittest.mock import Mock, patch

from src.models.paper import Paragraph, ParsedPaper
from src.translator import PaperTranslator


def test_translate_preserves_tables():
    with patch("src.translator.openai_translator.OpenAI") as mock:
        mock_client = Mock()
        mock_client.chat.completions.create.return_value.choices = [
            Mock(message=Mock(content="번역된 텍스트"))
        ]
        mock.return_value = mock_client

        translator = PaperTranslator(api_key="test")
        paper = ParsedPaper(
            body=[Paragraph(text="Hello", page=0, bbox=[0, 0, 0, 0])],
            tables=[{"html": "<table></table>"}],
            figures=[],
            equations=[],
            metadata={},
        )

        result = translator.translate(paper, "ko")
        assert result.tables == paper.tables
        assert result.body[0].text == "번역된 텍스트"
