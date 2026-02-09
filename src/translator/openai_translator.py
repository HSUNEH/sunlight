import asyncio
import logging
import os
import re

from openai import AsyncOpenAI, OpenAI

from src.models.paper import Paragraph, ParsedPaper

logger = logging.getLogger(__name__)


class PaperTranslator:
    SEPARATOR = "---PARAGRAPH_SEPARATOR---"

    SYSTEM_PROMPT_BATCH = (
        "You are an expert academic translator. "
        "Translate the following academic text to {target_lang}.\n\n"
        "## Rules\n"
        "1. For important technical terms, append the original English term in "
        "parentheses on its first occurrence. "
        "Example: '강화 학습(Reinforcement Learning)'\n"
        "2. NEVER modify LaTeX equations (anything between $...$, $$...$$, "
        "\\(...\\), \\[...\\], or \\begin{{...}}...\\end{{...}}). "
        "Output them exactly as they appear in the source.\n"
        "3. Maintain a natural, formal academic writing style appropriate for "
        "published papers.\n"
        "4. Output ONLY the translated text. Do not include any commentary, "
        "notes, or explanations.\n"
        "5. Preserve the separator '{separator}' exactly as-is between "
        "paragraphs. The number of separated segments in your output MUST "
        "equal the number in the input.\n"
    )

    SYSTEM_PROMPT_SINGLE = (
        "You are an expert academic translator. "
        "Translate the following academic text to {target_lang}.\n\n"
        "## Rules\n"
        "1. For important technical terms, append the original English term in "
        "parentheses on its first occurrence. "
        "Example: '강화 학습(Reinforcement Learning)'\n"
        "2. NEVER modify LaTeX equations (anything between $...$, $$...$$, "
        "\\(...\\), \\[...\\], or \\begin{{...}}...\\end{{...}}). "
        "Output them exactly as they appear in the source.\n"
        "3. Maintain a natural, formal academic writing style appropriate for "
        "published papers.\n"
        "4. Output ONLY the translated text. Do not include any commentary, "
        "notes, or explanations.\n"
    )

    # Pattern to detect text that is purely LaTeX math (possibly with whitespace)
    _LATEX_ONLY_RE = re.compile(
        r"^\s*("
        r"\$\$[\s\S]+?\$\$"        # $$...$$
        r"|\$[^\$]+\$"             # $...$
        r"|\\[\(\[][\s\S]+?\\[\)\]]"  # \(...\) or \[...\]
        r"|\\begin\{[^}]+\}[\s\S]+?\\end\{[^}]+\}"  # \begin{...}...\end{...}
        r")\s*$"
    )

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.async_client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    @staticmethod
    def _should_skip_translation(text: str) -> bool:
        """Return True if *text* should not be sent for translation.

        Skip conditions:
        - Empty or whitespace-only text.
        - Text consisting entirely of LaTeX math expression(s).
        - Very short text (3 words or fewer) that contains no alphabetic content
          worth translating.
        """
        stripped = text.strip()
        if not stripped:
            return True

        # Pure LaTeX math -- keep original
        if PaperTranslator._LATEX_ONLY_RE.match(stripped):
            return True

        # Very short text: 3 words or fewer
        words = stripped.split()
        if len(words) <= 3:
            # If all "words" are non-alphabetic (numbers, symbols, single
            # chars), skip translation.
            alpha_words = [w for w in words if re.search(r"[a-zA-Z]{2,}", w)]
            if not alpha_words:
                return True

        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate(self, paper: ParsedPaper, target_lang: str = "ko") -> ParsedPaper:
        """Batch translate body text while preserving tables, figures, and equations."""
        translated_body = []
        batch_size = 25

        for i in range(0, len(paper.body), batch_size):
            batch = paper.body[i : i + batch_size]
            texts = [para.text for para in batch]
            translated_texts = self._translate_batch(texts, target_lang)

            for j, trans_text in enumerate(translated_texts):
                translated_body.append(
                    Paragraph(text=trans_text, page=batch[j].page, bbox=batch[j].bbox)
                )

        return ParsedPaper(
            body=translated_body,
            tables=paper.tables,
            figures=paper.figures,
            equations=paper.equations,
            metadata=paper.metadata,
        )

    async def translate_async(
        self,
        paper: ParsedPaper,
        target_lang: str = "ko",
        batch_size: int = 25,
    ) -> ParsedPaper:
        """Batch translate in parallel using async requests.

        Paragraphs that should be skipped (math-only, very short, empty) are
        kept as-is and excluded from the API call to save tokens and latency.
        """
        translated_body: list[Paragraph] = [None] * len(paper.body)  # type: ignore[list-item]

        # 1) Pre-fill paragraphs that should be skipped
        indices_to_translate: list[int] = []
        for idx, para in enumerate(paper.body):
            if self._should_skip_translation(para.text):
                translated_body[idx] = Paragraph(
                    text=para.text, page=para.page, bbox=para.bbox
                )
                logger.debug("Skipping translation for paragraph %d: %r", idx, para.text[:60])
            else:
                indices_to_translate.append(idx)

        # 2) Build batches only from paragraphs that need translation
        batches: list[tuple[list[int], list[Paragraph], list[str]]] = []
        for i in range(0, len(indices_to_translate), batch_size):
            chunk_indices = indices_to_translate[i : i + batch_size]
            chunk_paras = [paper.body[ci] for ci in chunk_indices]
            chunk_texts = [p.text for p in chunk_paras]
            batches.append((chunk_indices, chunk_paras, chunk_texts))

        semaphore = asyncio.Semaphore(3)

        async def _do_batch(texts: list[str], lang: str) -> list[str]:
            async with semaphore:
                return await self._translate_batch_async(texts, lang)

        tasks = [_do_batch(texts, target_lang) for _, _, texts in batches]
        results = await asyncio.gather(*tasks)

        # 3) Place translated texts back at their original indices
        for (chunk_indices, chunk_paras, _), trans_texts in zip(batches, results):
            for ci, para, trans in zip(chunk_indices, chunk_paras, trans_texts):
                translated_body[ci] = Paragraph(
                    text=trans, page=para.page, bbox=para.bbox
                )

        return ParsedPaper(
            body=translated_body,
            tables=paper.tables,
            figures=paper.figures,
            equations=paper.equations,
            metadata=paper.metadata,
        )

    # ------------------------------------------------------------------
    # Batch translation (sync)
    # ------------------------------------------------------------------

    def _translate_batch(self, texts: list[str], target_lang: str) -> list[str]:
        """Translate multiple text blocks in a single request."""
        if not texts:
            return []

        separator = f"\n{self.SEPARATOR}\n"
        combined = separator.join(texts)
        system_prompt = self.SYSTEM_PROMPT_BATCH.format(
            target_lang=target_lang, separator=self.SEPARATOR
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": combined},
                ],
                timeout=60,
            )
            result = response.choices[0].message.content

            translated = [t.strip() for t in result.split(self.SEPARATOR)]

            if len(translated) != len(texts):
                logger.warning(
                    "Batch count mismatch: got %d, expected %d. "
                    "Falling back to individual translation.",
                    len(translated),
                    len(texts),
                )
                return [self._translate_text(t, target_lang) for t in texts]

            return translated
        except Exception as exc:
            logger.error("Batch translation error: %s", exc)
            return [self._translate_text(t, target_lang) for t in texts]

    # ------------------------------------------------------------------
    # Batch translation (async) -- with 1 retry on count mismatch
    # ------------------------------------------------------------------

    async def _translate_batch_async(self, texts: list[str], target_lang: str) -> list[str]:
        """Translate multiple text blocks in a single async request.

        If the number of returned segments does not match the input, one retry
        is attempted before falling back to individual translation.
        """
        if not texts:
            return []

        separator = f"\n{self.SEPARATOR}\n"
        combined = separator.join(texts)
        system_prompt = self.SYSTEM_PROMPT_BATCH.format(
            target_lang=target_lang, separator=self.SEPARATOR
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": combined},
        ]

        max_attempts = 2  # initial + 1 retry
        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    timeout=60,
                )
                result = response.choices[0].message.content
                translated = [t.strip() for t in result.split(self.SEPARATOR)]

                if len(translated) == len(texts):
                    return translated

                logger.warning(
                    "Batch count mismatch (attempt %d/%d): got %d, expected %d.",
                    attempt,
                    max_attempts,
                    len(translated),
                    len(texts),
                )

                if attempt < max_attempts:
                    logger.info("Retrying batch translation...")
                    continue

                # Exhausted retries -- fall back to individual
                logger.warning(
                    "Batch retry exhausted. Falling back to individual translation "
                    "for %d paragraphs.",
                    len(texts),
                )
                tasks = [self._translate_text_async(t, target_lang) for t in texts]
                return await asyncio.gather(*tasks)

            except Exception as exc:
                logger.error(
                    "Async batch error (attempt %d/%d): %s", attempt, max_attempts, exc
                )
                if attempt < max_attempts:
                    logger.info("Retrying batch translation after error...")
                    continue

                logger.warning(
                    "Batch retry exhausted after error. Falling back to individual "
                    "translation for %d paragraphs.",
                    len(texts),
                )
                tasks = [self._translate_text_async(t, target_lang) for t in texts]
                return await asyncio.gather(*tasks)

        # Should not be reached, but satisfy type checker
        return texts  # pragma: no cover

    # ------------------------------------------------------------------
    # Single-paragraph translation
    # ------------------------------------------------------------------

    def _translate_text(self, text: str, target_lang: str) -> str:
        """Translate a single text string."""
        if self._should_skip_translation(text):
            return text

        system_prompt = self.SYSTEM_PROMPT_SINGLE.format(target_lang=target_lang)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content

    async def _translate_text_async(self, text: str, target_lang: str) -> str:
        """Translate a single text string asynchronously."""
        if self._should_skip_translation(text):
            return text

        system_prompt = self.SYSTEM_PROMPT_SINGLE.format(target_lang=target_lang)

        response = await self.async_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content
