#!/usr/bin/env python3
"""
Auto-generate lesson content for a Bhagavatam chapter using GPT-4o-mini.

Takes extracted verse text and produces structured lesson data including
story narration, word breakdowns, quizzes, and Madhvacharya's teachings.
This enables scaling to all 335 chapters without manual content creation.

Prerequisites:
    - Set OPENAI_API_KEY in app/.env.local
    - Optionally run extract-english.py first for verse data

Usage:
    # Generate a single lesson with explicit content:
    python scripts/generate-lesson.py --skandha 1 --chapter 1 \\
        --title "Questions by the Sages" \\
        --verse "जन्माद्यस्य यतः" \\
        --translation "The Supreme Truth from whom everything emanates"

    # Generate from previously extracted data:
    python scripts/generate-lesson.py --skandha 1 --chapter 1 --from-extracted

    # Batch generate for an entire skandha:
    python scripts/generate-lesson.py --batch --skandha 1

Output:
    data/generated-lessons/S-C.json  (e.g., 1-1.json for Skandha 1, Chapter 1)
"""
import os
import sys
import json
import argparse
import time
from typing import Optional

from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env.local")
load_dotenv(ENV_PATH)

from openai import OpenAI, APIError, RateLimitError

MODEL = "gpt-4.1"
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0
BATCH_DELAY_SECONDS = 2.0

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "generated-lessons")
EXTRACTED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "english-extracted.json")

VALID_CHARACTER_IDS = [
    "krishna", "vishnu", "brahma", "shiva", "suta", "shaunaka",
    "vyasa", "shukadeva", "parikshit", "narada", "madhvacharya",
    "lakshmi", "indra", "prahlada", "dhruva", "kapila", "devahuti",
    "uddhava", "maitreya", "vidura", "kunti", "draupadi", "arjuna",
]


def build_prompt(skandha: int, chapter: int, title: str, verse_text: str, translation: str) -> str:
    """Build the generation prompt for a lesson."""
    return f"""You are creating educational content for a gamified Bhagavatam learning app \
that teaches Sanskrit and Madhvacharya's Dvaita Vedanta philosophy.

Generate a complete lesson for:
- Skandha {skandha}, Chapter {chapter}: "{title}"
- Key verse text (Sanskrit): {verse_text or "(not provided — select the most important verse from this chapter)"}
- Translation: {translation or "(not provided — use your knowledge of Srimad Bhagavatam)"}

Output VALID JSON with this exact structure:
{{
  "id": "{skandha}-{chapter}",
  "skandha": {skandha},
  "num": {chapter},
  "title": "{title or f'Skandha {skandha}, Chapter {chapter}'}",
  "desc": "One sentence description of this chapter",
  "story": [
    {{"type": "narration", "text": "..."}},
    {{"type": "dialogue", "speaker": "Character Name", "text": "..."}},
    // 5-6 story beats total, mixing narration and dialogue
  ],
  "verse": {{
    "ref": "Srimad Bhagavatam {skandha}.{chapter}.X",
    "sanskrit": "The key verse in Devanagari",
    "transliteration": "IAST transliteration",
    "translation": "English translation",
    "syllables": ["each", "syllable", "separately"],
    "words": [
      // EVERY SINGLE word from the verse
      {{"san": "देवनागरी", "trans": "transliteration", "mean": "brief meaning", "full": "detailed explanation"}}
    ]
  }},
  "madhvaTeaching": "Madhvacharya's interpretation emphasizing Dvaita philosophy (2-3 sentences, mention key Sanskrit terms)",
  "sanskritWords": [
    // Same words as verse.words but with example field added
    {{"san": "देवनागरी", "trans": "transliteration", "mean": "meaning", "example": "usage example from verse"}}
  ],
  "characterIds": ["list", "of", "character", "ids"],
  "quiz": [
    // 5 questions mixing mcq, fill, match types
    {{"type": "mcq", "question": "...", "options": ["A","B","C","D"], "correct": 0, "explanation": "..."}},
    {{"type": "fill", "question": "... ___", "answer": "Sanskrit word", "options": ["4 choices"], "explanation": "..."}},
    {{"type": "match", "question": "Match:", "pairs": [["Sanskrit","English"],["Sanskrit","English"],["Sanskrit","English"]], "explanation": "..."}}
  ],
  "boss": [
    // 4 harder comprehensive questions mixing all types
  ]
}}

IMPORTANT RULES:
- Include ALL Sanskrit words from the verse, not just key ones
- Story should be engaging narrative that brings the scene to life, not dry academic text
- Madhva's teaching should specifically highlight Dvaita vs Advaita differences where relevant
- Quiz questions should test both story comprehension and Sanskrit vocabulary
- Valid character IDs: {', '.join(VALID_CHARACTER_IDS)}
- Boss questions should be harder and require deeper understanding
- Make it educational AND fun for a mobile app audience
- Every word in verse.words must have all four fields: san, trans, mean, full"""


def generate_lesson(
    client: OpenAI,
    skandha: int,
    chapter: int,
    verse_text: str = "",
    translation: str = "",
    title: str = "",
) -> dict:
    """
    Generate full lesson content for a chapter using GPT-4o-mini.

    Returns:
        Parsed JSON dict with lesson structure.

    Raises:
        RuntimeError if generation fails after retries.
        json.JSONDecodeError if model output is not valid JSON.
    """
    prompt = build_prompt(skandha, chapter, title, verse_text, translation)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Sanskrit scholar and educational content creator. "
                        "Output ONLY valid JSON, no markdown fences or extra text.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=4096,
                temperature=0.7,
            )

            text = response.choices[0].message.content.strip()

            # Remove markdown fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3].strip()
                elif "```" in text:
                    text = text[: text.rfind("```")].strip()

            lesson = json.loads(text)

            # Validate essential fields
            required_fields = ["id", "skandha", "num", "title", "story", "verse", "quiz"]
            missing = [f for f in required_fields if f not in lesson]
            if missing:
                print(f"    WARNING: Missing fields in output: {missing}")

            return lesson

        except RateLimitError:
            wait = RETRY_BACKOFF_BASE ** attempt
            print(f"    Rate limited, waiting {wait:.0f}s (attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(wait)
        except json.JSONDecodeError as e:
            if attempt == MAX_RETRIES:
                print(f"    ERROR: Model returned invalid JSON: {e}", file=sys.stderr)
                print(f"    Raw output (first 200 chars): {text[:200]}", file=sys.stderr)
                raise
            print(f"    Invalid JSON, retrying (attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(1)
        except APIError as e:
            if attempt == MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF_BASE ** attempt
            print(f"    API error: {e}. Retrying in {wait:.0f}s...")
            time.sleep(wait)

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries")


def load_extracted_data() -> Optional[dict]:
    """Load previously extracted English verse data."""
    if not os.path.exists(EXTRACTED_PATH):
        return None
    with open(EXTRACTED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def find_chapter_in_extracted(
    data: dict, skandha: int, chapter: int
) -> tuple[str, str, str]:
    """
    Find a chapter in extracted data and return (title, verse_text, translation).
    Returns empty strings if not found.
    """
    for canto in data.get("cantos", []):
        if canto["number"] != skandha:
            continue
        for ch in canto.get("chapters", []):
            if ch["number"] != chapter:
                continue
            title = ch.get("title", "")
            # Get the first verse's translation as representative text
            verses = ch.get("verses", [])
            if verses:
                first_verse = verses[0]
                verse_text = first_verse.get("sanskrit_transliteration", "")
                translation = first_verse.get("translation", "")
                return title, verse_text, translation
            return title, "", ""
    return "", "", ""


def generate_single(args, client: OpenAI) -> None:
    """Generate a single lesson."""
    verse_text = args.verse or ""
    translation = args.translation or ""
    title = args.title or ""

    # Try loading from extracted data if requested
    if args.from_extracted:
        extracted = load_extracted_data()
        if extracted:
            ex_title, ex_verse, ex_trans = find_chapter_in_extracted(
                extracted, args.skandha, args.chapter
            )
            title = title or ex_title
            verse_text = verse_text or ex_verse
            translation = translation or ex_trans
            print(f"  Loaded from extracted data: title='{title[:50]}...'")
        else:
            print(f"  WARNING: No extracted data found at {EXTRACTED_PATH}")

    print(f"Generating lesson for Skandha {args.skandha}, Chapter {args.chapter}...")
    lesson = generate_lesson(
        client, args.skandha, args.chapter, verse_text, translation, title
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{args.skandha}-{args.chapter}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(lesson, f, ensure_ascii=False, indent=2)

    print(f"Saved to {output_path}")
    print(f"  Title:          {lesson.get('title', 'N/A')}")
    print(f"  Story beats:    {len(lesson.get('story', []))}")
    print(f"  Sanskrit words: {len(lesson.get('sanskritWords', []))}")
    print(f"  Quiz questions: {len(lesson.get('quiz', []))}")
    print(f"  Boss questions: {len(lesson.get('boss', []))}")


def generate_batch(args, client: OpenAI) -> None:
    """Generate lessons for all chapters in a skandha (or all skandhas)."""
    extracted = load_extracted_data()
    if not extracted:
        print(f"ERROR: Batch mode requires extracted data at {EXTRACTED_PATH}", file=sys.stderr)
        print("Run extract-english.py first.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cantos_to_process = extracted["cantos"]
    if args.skandha:
        cantos_to_process = [c for c in cantos_to_process if c["number"] == args.skandha]

    total_generated = 0
    total_skipped = 0
    total_errors = 0

    for canto in cantos_to_process:
        skandha = canto["number"]
        print(f"\n=== Skandha {skandha} ({len(canto['chapters'])} chapters) ===")

        for ch in canto["chapters"]:
            chapter = ch["number"]
            output_path = os.path.join(OUTPUT_DIR, f"{skandha}-{chapter}.json")

            if os.path.exists(output_path) and not args.force:
                print(f"  {skandha}-{chapter}: already exists, skipping")
                total_skipped += 1
                continue

            title = ch.get("title", "")
            verses = ch.get("verses", [])
            verse_text = verses[0].get("sanskrit_transliteration", "") if verses else ""
            translation = verses[0].get("translation", "") if verses else ""

            print(f"  {skandha}-{chapter}: Generating...")

            try:
                lesson = generate_lesson(
                    client, skandha, chapter, verse_text, translation, title
                )
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(lesson, f, ensure_ascii=False, indent=2)

                total_generated += 1
                print(f"    Done ({len(lesson.get('quiz', []))} quiz questions)")

                # Delay between API calls
                time.sleep(BATCH_DELAY_SECONDS)

            except Exception as e:
                print(f"    ERROR: {e}", file=sys.stderr)
                total_errors += 1

    print(f"\nBatch complete:")
    print(f"  Generated: {total_generated}")
    print(f"  Skipped:   {total_skipped}")
    print(f"  Errors:    {total_errors}")
    print(f"  Output:    {OUTPUT_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-generate Bhagavatam lesson content using GPT-4o-mini"
    )
    parser.add_argument("--skandha", type=int, help="Skandha (canto) number (1-12)")
    parser.add_argument("--chapter", type=int, help="Chapter number")
    parser.add_argument("--title", type=str, default="", help="Chapter title")
    parser.add_argument("--verse", type=str, default="", help="Sanskrit verse text")
    parser.add_argument("--translation", type=str, default="", help="English translation")
    parser.add_argument(
        "--from-extracted",
        action="store_true",
        help="Load verse data from extract-english.py output",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Generate lessons for all chapters (requires --from-extracted data)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if output already exists",
    )
    args = parser.parse_args()

    # Validate arguments
    if not args.batch and (args.skandha is None or args.chapter is None):
        print("ERROR: --skandha and --chapter are required (unless using --batch)", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if args.batch and args.chapter is not None:
        print("ERROR: --chapter is not used with --batch (processes all chapters)", file=sys.stderr)
        sys.exit(1)

    # Validate API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.", file=sys.stderr)
        print(f"Add it to {ENV_PATH} or set it as an environment variable.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI()

    if args.batch:
        generate_batch(args, client)
    else:
        generate_single(args, client)


if __name__ == "__main__":
    main()
