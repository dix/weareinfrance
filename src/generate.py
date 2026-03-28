from __future__ import annotations

import csv
import shutil
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


PAGE_SIZE = 10
BASE_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = BASE_DIR / "data" / "translations.csv"
TEMPLATES_DIR = BASE_DIR / "templates"
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "www"


@dataclass(frozen=True)
class PageInfo:
    num: int
    filename: str
    is_current: bool


def load_rows() -> list[dict[str, str]]:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing CSV: {CSV_PATH}")

    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV must include a header row: en,fr")
        header = [name.strip() for name in reader.fieldnames]
        if header != ["en", "fr"]:
            raise ValueError(f"CSV header must be 'en,fr', got: {header}")

        rows = []
        for row in reader:
            rows.append(
                {
                    "en": (row.get("en") or "").strip(),
                    "fr": (row.get("fr") or "").strip(),
                }
            )
    return rows


def chunk_rows(rows: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


def filename_for_page(page_num: int) -> str:
    if page_num == 1:
        return "index.html"
    return f"page_{page_num:03d}.html"


def build_pages(rows: list[dict[str, str]]) -> None:
    pages_data = chunk_rows(rows, PAGE_SIZE) or [[]]
    total_pages = len(pages_data)

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for existing in OUTPUT_DIR.glob("page_*.html"):
        existing.unlink()
    index_path = OUTPUT_DIR / "index.html"
    if index_path.exists():
        index_path.unlink()

    for page_num, entries in enumerate(pages_data, start=1):
        pages = [
            PageInfo(num=i, filename=filename_for_page(i), is_current=i == page_num)
            for i in range(1, total_pages + 1)
        ]
        template_name = "index.html" if page_num == 1 else "page.html"
        template = env.get_template(template_name)
        html = template.render(
            entries=entries,
            page_num=page_num,
            total_pages=total_pages,
            total_entries=len(rows),
            pages=pages,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )

        output_path = OUTPUT_DIR / filename_for_page(page_num)
        output_path.write_text(html, encoding="utf-8")


def copy_assets() -> None:
    target = OUTPUT_DIR / "assets"
    if target.exists():
        shutil.rmtree(target)
    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, target)


def main() -> None:
    rows = load_rows()
    build_pages(rows)
    copy_assets()
    print(f"Generated {len(rows)} entries into '{OUTPUT_DIR}'.")


if __name__ == "__main__":
    main()
