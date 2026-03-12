#!/usr/bin/env python3
"""
Extract text from the English Bhagavatam translation PDF.

This script processes 'srimad-bhagavata-mahapurana-english-translations.pdf'
(Prabhupada's translation, 1284 pages with selectable text) and outputs
structured JSON with verses organized by skandha (canto) and chapter.

Usage:
    python scripts/extract-english.py
    python scripts/extract-english.py --preview   # Show first 50 lines only
    python scripts/extract-english.py --stats      # Show structure stats only

Output:
    data/english-extracted.json
"""
import fitz  # PyMuPDF
import json
import re
import os
import sys
import argparse
from typing import Optional

PDF_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'srimad-bhagavata-mahapurana-english-translations.pdf')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'english-extracted.json')

# Pre-compiled patterns for verse parsing
CANTO_PATTERN = re.compile(r'(?:Canto|CANTO|Skandha)\s+(\d+)', re.IGNORECASE)
CHAPTER_PATTERN = re.compile(r'^(?:Chapter|CHAPTER)\s+(\d+)', re.IGNORECASE)
VERSE_PATTERN = re.compile(r'^(?:TEXT|TEXTS?)\s+(\d+(?:\s*-\s*\d+)?)', re.IGNORECASE)
PURPORT_PATTERN = re.compile(r'^PURPORT', re.IGNORECASE)
SYNONYMS_PATTERN = re.compile(r'^(?:SYNONYMS|Word[- ]?(?:for[- ]?)?[Ww]ord)', re.IGNORECASE)
TRANSLATION_PATTERN = re.compile(r'^TRANSLATION', re.IGNORECASE)

PAGE_BREAK = "\n---PAGE_BREAK---\n"


def extract_all_text() -> str:
    """Extract all selectable text from the PDF, page by page."""
    if not os.path.exists(PDF_PATH):
        print(f"ERROR: PDF not found at {PDF_PATH}", file=sys.stderr)
        print("Expected: srimad-bhagavata-mahapurana-english-translations.pdf", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(PDF_PATH)
    print(f"  PDF has {len(doc)} pages")

    full_text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        full_text += text + PAGE_BREAK

        if (page_num + 1) % 200 == 0:
            print(f"  Extracted {page_num + 1}/{len(doc)} pages...")

    doc.close()
    return full_text


def parse_verses(text: str) -> dict:
    """
    Parse extracted text into structured verse data.

    The PDF text follows patterns like:
    - Canto headers: "Canto X" or "CANTO X"
    - Chapter headers: "Chapter X" or "CHAPTER X"
    - Verse numbers: "TEXT X" or "TEXTS X-Y"
    - Sections: SYNONYMS, TRANSLATION, PURPORT

    Returns a dict with structure:
        { "cantos": [ { "number": N, "chapters": [ { "number": N, "title": "", "verses": [...] } ] } ] }
    """
    result = {"cantos": []}

    current_canto: Optional[dict] = None
    current_chapter: Optional[dict] = None
    current_verse: Optional[dict] = None
    current_section: Optional[str] = None  # 'synonyms', 'translation', 'purport', or None

    lines = text.split("\n")
    total_lines = len(lines)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped == "---PAGE_BREAK---":
            continue

        # --- Detect canto ---
        canto_match = CANTO_PATTERN.search(stripped)
        if canto_match and len(stripped) < 80:
            canto_num = int(canto_match.group(1))
            if 1 <= canto_num <= 12:
                if not current_canto or current_canto["number"] != canto_num:
                    current_canto = {"number": canto_num, "chapters": []}
                    result["cantos"].append(current_canto)
                    current_chapter = None
                    current_verse = None
                    current_section = None
                continue

        # --- Detect chapter ---
        chapter_match = CHAPTER_PATTERN.match(stripped)
        if chapter_match and current_canto:
            ch_num = int(chapter_match.group(1))
            current_chapter = {
                "number": ch_num,
                "title": "",
                "verses": [],
            }
            current_canto["chapters"].append(current_chapter)
            current_verse = None
            current_section = None

            # Look ahead for chapter title (next non-empty, non-verse line)
            for j in range(i + 1, min(i + 5, total_lines)):
                candidate = lines[j].strip()
                if candidate and candidate != "---PAGE_BREAK---":
                    if not VERSE_PATTERN.match(candidate) and not CHAPTER_PATTERN.match(candidate):
                        current_chapter["title"] = candidate
                    break
            continue

        # --- Detect verse ---
        verse_match = VERSE_PATTERN.match(stripped)
        if verse_match and current_chapter is not None:
            verse_num = verse_match.group(1).replace(" ", "")
            current_verse = {
                "number": verse_num,
                "sanskrit_transliteration": [],
                "synonyms": [],
                "translation": [],
                "purport": [],
            }
            current_chapter["verses"].append(current_verse)
            current_section = None
            continue

        # --- Detect section markers ---
        if SYNONYMS_PATTERN.match(stripped):
            current_section = "synonyms"
            continue
        if TRANSLATION_PATTERN.match(stripped):
            current_section = "translation"
            continue
        if PURPORT_PATTERN.match(stripped):
            current_section = "purport"
            continue

        # --- Accumulate text into current verse section ---
        if current_verse is not None:
            if current_section == "synonyms":
                current_verse["synonyms"].append(stripped)
            elif current_section == "translation":
                current_verse["translation"].append(stripped)
            elif current_section == "purport":
                current_verse["purport"].append(stripped)
            elif current_section is None:
                # Before any section marker = Sanskrit transliteration
                current_verse["sanskrit_transliteration"].append(stripped)

    return result


def consolidate_text_fields(result: dict) -> dict:
    """Join list-of-lines fields into single strings for cleaner output."""
    for canto in result["cantos"]:
        for chapter in canto["chapters"]:
            for verse in chapter["verses"]:
                verse["sanskrit_transliteration"] = "\n".join(
                    verse["sanskrit_transliteration"]
                ).strip()
                verse["synonyms"] = "\n".join(verse["synonyms"]).strip()
                verse["translation"] = "\n".join(verse["translation"]).strip()
                verse["purport"] = "\n".join(verse["purport"]).strip()
    return result


def print_stats(result: dict) -> None:
    """Print summary statistics of the extracted data."""
    total_verses = 0
    total_chapters = 0
    print("\n  Skandha | Chapters | Verses")
    print("  --------|----------|-------")
    for canto in result["cantos"]:
        ch_count = len(canto["chapters"])
        v_count = sum(len(ch["verses"]) for ch in canto["chapters"])
        total_chapters += ch_count
        total_verses += v_count
        print(f"  {canto['number']:>7} | {ch_count:>8} | {v_count:>6}")
    print("  --------|----------|-------")
    print(f"  {'Total':>7} | {total_chapters:>8} | {total_verses:>6}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract text from the English Bhagavatam translation PDF"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Extract and show first 50 lines of raw text only",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show extraction stats without saving (requires previous extraction)",
    )
    args = parser.parse_args()

    # Stats-only mode: load existing output
    if args.stats:
        if not os.path.exists(OUTPUT_PATH):
            print("ERROR: No existing extraction found. Run without --stats first.", file=sys.stderr)
            sys.exit(1)
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            result = json.load(f)
        print_stats(result)
        return

    print("Extracting text from English translation PDF...")
    text = extract_all_text()
    print(f"  Extracted {len(text):,} characters total")

    # Preview mode
    if args.preview:
        preview_lines = text.split("\n")[:50]
        for line in preview_lines:
            print(f"  | {line}")
        return

    print("Parsing verses...")
    result = parse_verses(text)
    result = consolidate_text_fields(result)

    print_stats(result)

    # Save output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
