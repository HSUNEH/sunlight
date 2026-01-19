import asyncio
import os

from openai import AsyncOpenAI, OpenAI

from src.models.paper import Paragraph, ParsedPaper


class PaperTranslator:
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.async_client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

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
        """Batch translate in parallel using async requests."""
        batches = []

        for i in range(0, len(paper.body), batch_size):
            batch = paper.body[i : i + batch_size]
            texts = [para.text for para in batch]
            batches.append((i, batch, texts))

        semaphore = asyncio.Semaphore(3)

        async def translate_batch_async(texts: list[str], lang: str) -> list[str]:
            async with semaphore:
                return await self._translate_batch_async(texts, lang)

        tasks = [translate_batch_async(texts, target_lang) for _, _, texts in batches]
        results = await asyncio.gather(*tasks)

        translated_body = []
        for (_, batch, _), translated_texts in zip(batches, results):
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

    def _translate_batch(self, texts: list[str], target_lang: str) -> list[str]:
        """Translate multiple text blocks in a single request."""
        if not texts:
            return []

        separator = "\n---PARAGRAPH_SEPARATOR---\n"
        combined = separator.join(texts)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate the following academic text to "
                            f"{target_lang}. Keep the separator "
                            "'---PARAGRAPH_SEPARATOR---' as-is. "
                            "Preserve LaTeX equations."
                        ),
                    },
                    {"role": "user", "content": combined},
                ],
                timeout=60,
            )
            result = response.choices[0].message.content

            translated = result.split("---PARAGRAPH_SEPARATOR---")
            translated = [t.strip() for t in translated]

            if len(translated) != len(texts):
                return [self._translate_text(t, target_lang) for t in texts]

            return translated
        except Exception as exc:
            print(f"Batch translation error: {exc}")
            return [self._translate_text(t, target_lang) for t in texts]

    async def _translate_batch_async(self, texts: list[str], target_lang: str) -> list[str]:
        """Translate multiple text blocks in a single async request."""
        if not texts:
            return []

        separator = "\n---PARAGRAPH_SEPARATOR---\n"
        combined = separator.join(texts)

        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Translate to {target_lang}. Keep "
                            "'---PARAGRAPH_SEPARATOR---' as-is. Preserve LaTeX."
                        ),
                    },
                    {"role": "user", "content": combined},
                ],
                timeout=60,
            )
            result = response.choices[0].message.content
            translated = [t.strip() for t in result.split("---PARAGRAPH_SEPARATOR---")]

            if len(translated) != len(texts):
                return [t for t in texts]
            return translated
        except Exception as exc:
            print(f"Async batch error: {exc}")
            return [t for t in texts]

    def _translate_text(self, text: str, target_lang: str) -> str:
        """Translate a single text string."""
        if not text.strip():
            return text

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate the following academic text to "
                        f"{target_lang}. Preserve LaTeX equations as-is. "
                        "Keep technical terms accurate."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content
