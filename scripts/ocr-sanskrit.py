#!/usr/bin/env python3
"""
Extract page images from the scanned Sanskrit Tatparya Nirnaya PDF.

This script processes 'Sri Bhagavata Tatparya Nirnaya.pdf' (Madhvacharya's
commentary, 863 pages, scanned/image-only) and extracts each page as a
high-resolution PNG image for subsequent OCR processing.

Pages are organized by approximate skandha (canto) based on known page ranges.
A manifest JSON file is generated to track all extracted pages.

Usage:
    python scripts/ocr-sanskrit.py --sample          # First 10 pages only
    python scripts/ocr-sanskrit.py --skandha 1       # Extract Skandha 1
    python scripts/ocr-sanskrit.py --pages 50-100    # Specific page range
    python scripts/ocr-sanskrit.py --dpi 300         # Higher quality
    python scripts/ocr-sanskrit.py                   # ALL pages (slow)

Output:
    data/sanskrit-pages/    — PNG images per page
    data/sanskrit-manifest.json — Extraction manifest
"""
import fitz  # PyMuPDF
import json
import os
import sys
import argparse
from typing import Optional

PDF_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "Sri Bhagavata Tatparya Nirnaya.pdf"
)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sanskrit-pages")
MANIFEST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "sanskrit-manifest.json"
)

# Approximate page ranges for each Skandha in the content (after front matter).
# These are content page numbers, not PDF page numbers.
# Adjust these after inspecting the actual PDF structure.
SKANDHA_PAGES = {
    1: (1, 63),
    2: (64, 134),
    3: (135, 273),
    4: (274, 358),
    5: (359, 394),
    6: (395, 428),
    7: (429, 497),
    8: (498, 560),
    9: (561, 630),
    10: (631, 750),
    11: (751, 820),
    12: (821, 848),
}

# Number of PDF pages before content page 1 (front matter, TOC, etc.).
# Adjust after inspecting the PDF. Content page 1 = PDF page (CONTENT_OFFSET + 1).
CONTENT_OFFSET = 19

DEFAULT_DPI = 200


def get_skandha_for_page(content_page: int) -> Optional[int]:
    """Determine which skandha a content page belongs to."""
    for skandha, (start, end) in SKANDHA_PAGES.items():
        if start <= content_page <= end:
            return skandha
    return None


def extract_pages(
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    dpi: int = DEFAULT_DPI,
    force: bool = False,
) -> dict:
    """
    Extract page images from the PDF.

    Args:
        start_page: First PDF page index (0-based). Defaults to 0.
        end_page: Last PDF page index (exclusive). Defaults to total pages.
        dpi: Resolution for rendered images.
        force: Re-extract even if image already exists.

    Returns:
        Manifest dict with extraction metadata.
    """
    if not os.path.exists(PDF_PATH):
        print(f"ERROR: PDF not found at {PDF_PATH}", file=sys.stderr)
        print("Expected: Sri Bhagavata Tatparya Nirnaya.pdf", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(PDF_PATH)
    total = len(doc)
    print(f"  PDF has {total} pages")

    start = start_page if start_page is not None else 0
    end = min(end_page if end_page is not None else total, total)

    manifest = {
        "source_pdf": os.path.basename(PDF_PATH),
        "total_pdf_pages": total,
        "content_offset": CONTENT_OFFSET,
        "dpi": dpi,
        "skandha_ranges": {str(k): list(v) for k, v in SKANDHA_PAGES.items()},
        "extracted": [],
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    extracted_count = 0
    skipped_count = 0

    for pdf_page in range(start, end):
        content_page = pdf_page - CONTENT_OFFSET
        if content_page < 1:
            continue

        skandha = get_skandha_for_page(content_page)
        filename = f"page_{content_page:04d}_sk{skandha or 0}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)

        entry = {
            "pdf_page": pdf_page,
            "content_page": content_page,
            "skandha": skandha,
            "filename": filename,
        }

        if os.path.exists(filepath) and not force:
            entry["status"] = "existing"
            skipped_count += 1
        else:
            try:
                page = doc[pdf_page]
                pix = page.get_pixmap(dpi=dpi)
                pix.save(filepath)
                entry["status"] = "extracted"
                extracted_count += 1
            except Exception as e:
                entry["status"] = "error"
                entry["error"] = str(e)
                print(f"  WARNING: Failed to extract page {pdf_page}: {e}", file=sys.stderr)

        manifest["extracted"].append(entry)

        # Progress reporting
        processed = pdf_page - start + 1
        if processed % 50 == 0 or pdf_page == end - 1:
            print(f"  Processed {processed}/{end - start} pages "
                  f"({extracted_count} new, {skipped_count} existing)")

    doc.close()
    return manifest


def main():
    parser = argparse.ArgumentParser(
        description="Extract page images from the scanned Sanskrit Tatparya Nirnaya PDF"
    )
    parser.add_argument(
        "--skandha",
        type=int,
        choices=range(1, 13),
        metavar="N",
        help="Extract only this skandha (1-12)",
    )
    parser.add_argument(
        "--pages",
        type=str,
        help='PDF page range (0-based), e.g., "20-80"',
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"DPI for image extraction (default: {DEFAULT_DPI})",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Extract just the first 10 content pages as a sample",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract pages even if images already exist",
    )
    args = parser.parse_args()

    if args.sample:
        print("Extracting sample (first 10 content pages)...")
        manifest = extract_pages(
            CONTENT_OFFSET, CONTENT_OFFSET + 10, args.dpi, args.force
        )
    elif args.skandha:
        if args.skandha not in SKANDHA_PAGES:
            print(f"ERROR: Unknown skandha {args.skandha}", file=sys.stderr)
            sys.exit(1)
        s, e = SKANDHA_PAGES[args.skandha]
        start_pdf = s + CONTENT_OFFSET - 1
        end_pdf = e + CONTENT_OFFSET
        print(f"Extracting Skandha {args.skandha} (content pages {s}-{e}, "
              f"PDF pages {start_pdf}-{end_pdf - 1})...")
        manifest = extract_pages(start_pdf, end_pdf, args.dpi, args.force)
    elif args.pages:
        try:
            start, end = map(int, args.pages.split("-"))
        except ValueError:
            print('ERROR: --pages must be in format "START-END"', file=sys.stderr)
            sys.exit(1)
        print(f"Extracting PDF pages {start}-{end}...")
        manifest = extract_pages(start, end + 1, args.dpi, args.force)
    else:
        print("Extracting ALL pages (this will take a while)...")
        manifest = extract_pages(dpi=args.dpi, force=args.force)

    # Save manifest
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    # Summary
    statuses = {}
    for entry in manifest["extracted"]:
        s = entry.get("status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1

    print(f"\nExtraction complete:")
    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")
    print(f"  Manifest saved to {MANIFEST_PATH}")
    print(f"  Images saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
