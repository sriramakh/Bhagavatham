#!/usr/bin/env python3
"""
OCR Sanskrit pages using GPT-4o vision API.

Reads page images extracted by ocr-sanskrit.py and sends them to GPT-4o-mini
for accurate Devanagari text extraction. GPT-4o vision is significantly more
accurate than Tesseract for Sanskrit/Devanagari OCR.

Prerequisites:
    - Run ocr-sanskrit.py first to extract page images
    - Set OPENAI_API_KEY in app/.env.local

Usage:
    python scripts/ocr-with-vision.py --sample       # Process 3 pages as test
    python scripts/ocr-with-vision.py --pages 1-10   # Process content pages 1-10
    python scripts/ocr-with-vision.py --skandha 1    # Process all of Skandha 1
    python scripts/ocr-with-vision.py                 # Process all extracted pages

Output:
    data/sanskrit-ocr/page_XXXX_skN.json  — Per-page OCR results
    data/sanskrit-ocr/_summary.json        — Processing summary
"""
import os
import sys
import json
import base64
import time
import argparse
from typing import Optional

# Load environment before importing OpenAI
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env.local")
load_dotenv(ENV_PATH)

from openai import OpenAI, APIError, RateLimitError

PAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sanskrit-pages")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sanskrit-ocr")
SUMMARY_PATH = os.path.join(OUTPUT_DIR, "_summary.json")

# OCR model — gpt-4o-mini is cost-effective; switch to gpt-4o for higher accuracy
MODEL = "gpt-4o-mini"

# Rate limiting
REQUEST_DELAY_SECONDS = 1.0
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0

SYSTEM_PROMPT = """You are an expert Sanskrit scholar and OCR specialist. \
Extract ALL text from this scanned page of Sri Bhagavata Tatparya Nirnaya by Madhvacharya.

Output the text in this structured JSON format:
{
  "verses": [
    {
      "ref": "X.Y.Z",
      "sanskrit": "Full verse in Devanagari script exactly as written",
      "commentary": "Any commentary text following the verse"
    }
  ],
  "page_header": "Any header text (skandha/chapter info)",
  "page_number": null,
  "other_text": "Any other text not part of verses"
}

IMPORTANT:
- Reproduce Devanagari characters with extreme precision
- Preserve all diacritical marks, visargas, anusvāras, and conjunct consonants
- Include verse reference numbers exactly as printed (e.g., १.१.१ or 1.1.1)
- If you cannot read a word clearly, mark it as [unclear]
- Output ONLY valid JSON, no markdown fences or extra text"""


def encode_image(image_path: str) -> str:
    """Read an image file and return its base64 encoding."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ocr_page(client: OpenAI, image_path: str) -> dict:
    """
    Use GPT-4o vision to OCR a single Sanskrit page.

    Args:
        client: OpenAI client instance.
        image_path: Path to the page image.

    Returns:
        Parsed JSON dict from the model response.

    Raises:
        Exception on API errors after retries.
    """
    b64 = encode_image(image_path)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please OCR this page of the Bhagavata Tatparya Nirnaya:",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64}",
                                    "detail": "high",
                                },
                            },
                        ],
                    },
                ],
                max_tokens=4096,
                temperature=0.1,  # Low temperature for faithful reproduction
            )

            raw_text = response.choices[0].message.content.strip()

            # Strip markdown fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3].strip()

            return json.loads(raw_text)

        except RateLimitError:
            wait = RETRY_BACKOFF_BASE ** attempt
            print(f"    Rate limited, waiting {wait:.0f}s (attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(wait)
        except json.JSONDecodeError:
            # Model returned non-JSON; wrap it
            return {"raw_text": raw_text, "parse_error": True}
        except APIError as e:
            if attempt == MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF_BASE ** attempt
            print(f"    API error: {e}. Retrying in {wait:.0f}s (attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(wait)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries")


def get_page_files(
    skandha: Optional[int] = None,
    page_range: Optional[str] = None,
    sample: bool = False,
) -> list[str]:
    """Get sorted list of page image filenames to process."""
    if not os.path.exists(PAGES_DIR):
        print(f"ERROR: Pages directory not found: {PAGES_DIR}", file=sys.stderr)
        print("Run ocr-sanskrit.py first to extract page images.", file=sys.stderr)
        sys.exit(1)

    pages = sorted(f for f in os.listdir(PAGES_DIR) if f.endswith(".png"))

    if not pages:
        print(f"ERROR: No PNG files found in {PAGES_DIR}", file=sys.stderr)
        sys.exit(1)

    if sample:
        return pages[:3]

    if skandha is not None:
        pages = [p for p in pages if f"_sk{skandha}." in p]

    if page_range:
        try:
            start, end = map(int, page_range.split("-"))
            pages = [
                p for p in pages
                if start <= int(p.split("_")[1]) <= end
            ]
        except (ValueError, IndexError):
            print(f'ERROR: Invalid page range "{page_range}". Use format "START-END".', file=sys.stderr)
            sys.exit(1)

    return pages


def main():
    parser = argparse.ArgumentParser(
        description="OCR Sanskrit pages using GPT-4o vision API"
    )
    parser.add_argument(
        "--pages",
        type=str,
        help='Process specific content pages, e.g., "1-10"',
    )
    parser.add_argument(
        "--skandha",
        type=int,
        choices=range(1, 13),
        metavar="N",
        help="Process pages from this skandha only (1-12)",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Process just 3 pages as a test",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process pages that already have OCR output",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=MODEL,
        help=f"OpenAI model to use (default: {MODEL})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY_SECONDS,
        help=f"Seconds between API requests (default: {REQUEST_DELAY_SECONDS})",
    )
    args = parser.parse_args()

    # Validate API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.", file=sys.stderr)
        print(f"Add it to {ENV_PATH} or set it as an environment variable.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    pages = get_page_files(
        skandha=args.skandha, page_range=args.pages, sample=args.sample
    )
    print(f"Processing {len(pages)} pages with model {args.model}...")

    results = []
    success_count = 0
    skip_count = 0
    error_count = 0

    for i, page_file in enumerate(pages):
        image_path = os.path.join(PAGES_DIR, page_file)
        output_file = os.path.join(OUTPUT_DIR, page_file.replace(".png", ".json"))

        # Skip already-processed pages unless --force
        if os.path.exists(output_file) and not args.force:
            print(f"  [{i + 1}/{len(pages)}] {page_file} — already processed, skipping")
            skip_count += 1
            results.append({"page": page_file, "status": "skipped"})
            continue

        print(f"  [{i + 1}/{len(pages)}] Processing {page_file}...")

        try:
            ocr_result = ocr_page(client, image_path)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "page": page_file,
                        "model": args.model,
                        "ocr_result": ocr_result,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            verse_count = len(ocr_result.get("verses", []))
            print(f"    Extracted {verse_count} verse(s)")
            results.append({"page": page_file, "status": "success", "verses": verse_count})
            success_count += 1

            # Rate limit delay
            if i < len(pages) - 1:
                time.sleep(args.delay)

        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            results.append({"page": page_file, "status": "error", "error": str(e)})
            error_count += 1

    # Save processing summary
    summary = {
        "model": args.model,
        "total_pages": len(pages),
        "success": success_count,
        "skipped": skip_count,
        "errors": error_count,
        "results": results,
    }
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nDone!")
    print(f"  Success: {success_count}")
    print(f"  Skipped: {skip_count}")
    print(f"  Errors:  {error_count}")
    print(f"  Summary: {SUMMARY_PATH}")
    print(f"  Output:  {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
