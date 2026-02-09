"""LatexNormalizer edge-case tests."""

from src.parser.latex_normalizer import LatexNormalizer


class TestLatexNormalizer:
    def setup_method(self):
        self.normalizer = LatexNormalizer()

    def test_empty_string(self):
        assert self.normalizer.normalize("") == ""

    def test_none_input(self):
        """None is falsy, so normalize should return it as-is."""
        assert self.normalizer.normalize(None) is None

    def test_command_brace_spacing_removed(self):
        r"""LaTeX 명령어와 중괄호 사이 공백 제거: \mathrm { x } -> \mathrm{x}"""
        result = self.normalizer.normalize(r"\mathrm { x }")
        assert result == r"\mathrm{x}"

    def test_command_brace_spacing_textbf(self):
        r"""\textbf { word } -> \textbf{word}"""
        result = self.normalizer.normalize(r"\textbf { word }")
        assert result == r"\textbf{word}"

    def test_subscript_spacing_removed(self):
        r"""첨자 공백 제거: x _ {i} -> x_{i}"""
        result = self.normalizer.normalize(r"$x _ {i}$")
        assert "_{i}" in result
        assert " _ {" not in result

    def test_superscript_spacing_removed(self):
        r"""첨자 공백 제거: x ^ {2} -> x^{2}"""
        result = self.normalizer.normalize(r"$x ^ {2}$")
        assert "^{2}" in result
        assert " ^ {" not in result

    def test_numbers_in_math_spacing_removed(self):
        r"""수식 내 숫자 공백 제거: $1 0 0$ -> $100$"""
        result = self.normalizer.normalize("$1 0 0$")
        assert result == "$100$"

    def test_decimal_point_spacing_removed(self):
        r"""소수점 주변 공백: $3 . 1 4$ -> $3.14$"""
        result = self.normalizer.normalize("$3 . 1 4$")
        assert result == "$3.14$"

    def test_text_command_content_spacing_removed(self):
        r"""\text{h e l l o} -> \text{hello}"""
        result = self.normalizer.normalize(r"\text{h e l l o}")
        assert result == r"\text{hello}"

    def test_text_command_content_with_mathrm(self):
        r"""\mathrm{a b c} -> \mathrm{abc}"""
        result = self.normalizer.normalize(r"\mathrm{a b c}")
        assert result == r"\mathrm{abc}"

    def test_plain_text_unchanged(self):
        """일반 텍스트(수식 없음)는 변경 없이 통과."""
        text = "This is a normal sentence with no LaTeX."
        result = self.normalizer.normalize(text)
        assert result == text

    def test_plain_text_with_numbers_unchanged(self):
        """수식 바깥의 숫자 공백은 변경하지 않아야 함."""
        text = "There are 1 0 0 items."
        result = self.normalizer.normalize(text)
        assert result == text

    def test_multiple_commands_in_one_string(self):
        r"""여러 LaTeX 명령어가 포함된 문자열."""
        text = r"\mathrm { X } and \textbf { Y }"
        result = self.normalizer.normalize(text)
        assert r"\mathrm{X}" in result
        assert r"\textbf{Y}" in result
