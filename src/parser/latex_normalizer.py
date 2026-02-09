"""MinerU OCR 결과의 LaTeX 수식 공백 정규화 모듈."""
from __future__ import annotations

import re


class LatexNormalizer:
    """LaTeX 수식 내 불필요한 공백을 정규화."""

    LATEX_COMMANDS = (
        "mathrm",
        "text",
        "mathbb",
        "mathbf",
        "mathit",
        "mathcal",
        "mathsf",
        "textbf",
        "textit",
        "textrm",
        "texttt",
    )

    def normalize(self, text: str) -> str:
        """수식 텍스트 정규화 메인 함수."""
        if not text:
            return text

        text = self._fix_command_braces(text)
        text = self._fix_brace_spacing(text)
        text = self._fix_subscript_superscript(text)
        text = self._fix_text_content(text)
        text = self._fix_numbers_in_math(text)
        text = self._fix_dollar_spacing(text)

        return text

    def _fix_command_braces(self, text: str) -> str:
        """LaTeX 명령어와 중괄호 사이 공백 제거."""
        commands_pattern = "|".join(self.LATEX_COMMANDS)
        pattern = rf"(\\(?:{commands_pattern}))\s*\{{\s*"
        return re.sub(pattern, r"\1{", text)

    def _fix_brace_spacing(self, text: str) -> str:
        """중괄호 내부 앞뒤 공백 제거."""
        text = re.sub(r"\{\s+", "{", text)
        text = re.sub(r"\s+\}", "}", text)
        return text

    def _fix_subscript_superscript(self, text: str) -> str:
        """첨자(_, ^)와 중괄호 사이 공백 제거."""
        text = re.sub(r"\s*_\s*\{", "_{", text)
        text = re.sub(r"\s*\^\s*\{", "^{", text)
        return text

    def _fix_text_content(self, text: str) -> str:
        r"""\\text{} 등 내부의 문자 사이 공백 제거."""

        def fix_content(match: re.Match) -> str:
            cmd = match.group(1)
            content = match.group(2)
            # 단일 공백으로 분리된 문자들을 붙임
            fixed = re.sub(r"(?<=\w)\s+(?=\w)", "", content)
            # 하이픈 주변 공백 정리
            fixed = re.sub(r"\s*-\s*", "-", fixed)
            return f"{cmd}{{{fixed}}}"

        commands_pattern = "|".join(self.LATEX_COMMANDS)
        pattern = rf"(\\(?:{commands_pattern}))\{{([^}}]+)\}}"
        return re.sub(pattern, fix_content, text)

    def _fix_numbers_in_math(self, text: str) -> str:
        """수식 내 숫자 사이 공백 및 기타 불필요한 공백 제거."""

        def fix_math_content(match: re.Match) -> str:
            content = match.group(1)
            # 숫자 사이 공백 제거 (여러 번 적용)
            for _ in range(3):
                content = re.sub(r"(\d)\s+(\d)", r"\1\2", content)
            # 소수점 주변 공백 제거
            content = re.sub(r"(\d)\s*\.\s*(\d)", r"\1.\2", content)
            # 괄호 내부 공백 제거: ( x ) -> (x)
            content = re.sub(r"\(\s+", "(", content)
            content = re.sub(r"\s+\)", ")", content)
            # 백슬래시 명령어 앞 공백 제거: 50 \% -> 50\%
            content = re.sub(r"(\d)\s+(\\)", r"\1\2", content)
            return f"${content}$"

        # 인라인 수식 $...$ 처리 (non-greedy)
        return re.sub(r"\$([^$]+)\$", fix_math_content, text)

    def _fix_dollar_spacing(self, text: str) -> str:
        """$ 기호 주변 불필요한 공백 정리."""
        # $와 내용 사이 공백 제거
        text = re.sub(r"\$\s+", "$", text)
        text = re.sub(r"\s+\$", "$", text)
        return text
