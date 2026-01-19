import argparse
from pathlib import Path

from dotenv import load_dotenv

from src.parser import PaperParser
from src.translator import PaperTranslator

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="논문 PDF 번역기")
    parser.add_argument("pdf", help="입력 PDF 파일 경로")
    parser.add_argument(
        "-o", "--output", default="translated.md", help="출력 Markdown 파일"
    )
    parser.add_argument(
        "-l", "--lang", default="ko", help="번역 대상 언어 (기본: ko)"
    )
    parser.add_argument("--no-translate", action="store_true", help="번역 없이 파싱만")
    args = parser.parse_args()

    print(f"파싱 중: {args.pdf}")
    paper_parser = PaperParser()
    parsed = paper_parser.parse(args.pdf)
    print(f"  - 본문: {len(parsed.body)}개 문단")
    print(f"  - 테이블: {len(parsed.tables)}개")
    print(f"  - 수식: {len(parsed.equations)}개")

    if not args.no_translate:
        print(f"번역 중: {args.lang}")
        translator = PaperTranslator()
        parsed = translator.translate(parsed, args.lang)

    output_path = Path(args.output)
    md_content = generate_markdown(parsed)
    output_path.write_text(md_content, encoding="utf-8")
    print(f"저장 완료: {output_path}")


def generate_markdown(paper) -> str:
    """ParsedPaper를 Markdown으로 변환."""
    lines: list[str] = []

    for para in paper.body:
        lines.append(para.text)
        lines.append("")

    if paper.equations:
        lines.append("---")
        lines.append("## Equations")
        for eq in paper.equations:
            lines.append(f"$${eq}$$")
            lines.append("")

    if paper.tables:
        lines.append("---")
        lines.append("## Tables")
        for i, table in enumerate(paper.tables):
            lines.append(f"### Table {i + 1}")
            html = getattr(table, "html", None)
            if html is None and isinstance(table, dict):
                html = table.get("html")
            lines.append(html or str(table))
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
