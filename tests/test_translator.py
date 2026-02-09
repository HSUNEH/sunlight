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


# ------------------------------------------------------------------
# _should_skip_translation tests
# ------------------------------------------------------------------


class TestShouldSkipTranslation:
    """PaperTranslator._should_skip_translation static method tests."""

    def test_empty_string(self):
        """빈 문자열 -> True."""
        assert PaperTranslator._should_skip_translation("") is True

    def test_whitespace_only(self):
        """공백만 -> True."""
        assert PaperTranslator._should_skip_translation("   ") is True
        assert PaperTranslator._should_skip_translation("\n\t") is True

    def test_pure_inline_latex(self):
        """순수 인라인 LaTeX $E = mc^2$ -> True."""
        assert PaperTranslator._should_skip_translation("$E = mc^2$") is True

    def test_pure_display_latex(self):
        r"""$$\int_0^1 f(x) dx$$ -> True."""
        assert PaperTranslator._should_skip_translation(r"$$\int_0^1 f(x) dx$$") is True

    def test_begin_end_equation(self):
        r"""\begin{equation}...\end{equation} -> True."""
        text = r"\begin{equation}E = mc^2\end{equation}"
        assert PaperTranslator._should_skip_translation(text) is True

    def test_latex_with_surrounding_whitespace(self):
        """LaTeX 수식에 앞뒤 공백이 있어도 skip."""
        assert PaperTranslator._should_skip_translation("  $x + y$  ") is True

    def test_normal_academic_text(self):
        """일반 학술 텍스트 -> False."""
        text = "This paper presents a novel approach to reinforcement learning."
        assert PaperTranslator._should_skip_translation(text) is False

    def test_numbers_only(self):
        """숫자만 '123' -> True (3단어 이하, 알파벳 없음)."""
        assert PaperTranslator._should_skip_translation("123") is True

    def test_figure_label(self):
        """'Figure 1' -> False (알파벳 단어 있음)."""
        assert PaperTranslator._should_skip_translation("Figure 1") is False

    def test_short_non_alpha(self):
        """짧은 비알파벳 텍스트 -> True."""
        assert PaperTranslator._should_skip_translation("1.2") is True
        assert PaperTranslator._should_skip_translation("+ - =") is True

    def test_short_with_alpha_word(self):
        """짧지만 알파벳 단어가 있으면 -> False."""
        assert PaperTranslator._should_skip_translation("Table 2") is False
        assert PaperTranslator._should_skip_translation("See above") is False

    def test_paren_latex_skip(self):
        r"""\( ... \) 형태 LaTeX -> True."""
        assert PaperTranslator._should_skip_translation(r"\( x + y \)") is True

    def test_bracket_latex_skip(self):
        r"""\[ ... \] 형태 LaTeX -> True."""
        assert PaperTranslator._should_skip_translation(r"\[ x^2 + y^2 = z^2 \]") is True
