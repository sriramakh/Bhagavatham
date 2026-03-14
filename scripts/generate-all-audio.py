#!/usr/bin/env python3
"""
Pre-generate ElevenLabs audio for all 335 chapter shlokas.

Reads verse.sanskrit from each generated lesson, calls ElevenLabs TTS
(Rachel voice, multilingual v2, speed 0.9), and saves as:
    public/audio/verses/{skandha}-{chapter}.mp3

Usage:
    python scripts/generate-all-audio.py              # All chapters
    python scripts/generate-all-audio.py --skandha 1  # Just skandha 1
    python scripts/generate-all-audio.py 1-1          # Single chapter
    python scripts/generate-all-audio.py --force      # Regenerate even if cached
"""
import os, sys, json, time, re
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(__file__)
LESSON_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')
AUDIO_DIR = os.path.join(SCRIPT_DIR, '..', 'public', 'audio', 'verses')

ELEVENLABS_URL = 'https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM'
RACHEL_VOICE_ID = '21m00Tcm4TlvDq8ikWAM'

# Load API key
from dotenv import load_dotenv
load_dotenv(os.path.join(SCRIPT_DIR, '..', '.env.local'))
API_KEY = os.environ.get('ELEVENLAB_API_KEY', '')


def is_consonant(ch):
    """Check if a character is a Devanagari consonant (क-ह)."""
    return '\u0915' <= ch <= '\u0939'


def add_schwa_hints(text):
    """Add explicit अ after word-final bare consonants to prevent Hindi schwa deletion.

    In Sanskrit, every consonant has an inherent 'a' (schwa) unless a halant (्) is present.
    Hindi TTS models drop this final 'a', so उवाच sounds like 'uvach' instead of 'uvacha'.
    Adding explicit अ forces the model to pronounce it.
    """
    chars = list(text)
    result = []
    for i, ch in enumerate(chars):
        result.append(ch)
        if is_consonant(ch):
            next_ch = chars[i + 1] if i + 1 < len(chars) else ' '
            if next_ch in (' ', '\n', '।', '॥') or i + 1 >= len(chars):
                result.append('अ')
    return ''.join(result)


def prepare_verse_text(sanskrit):
    """Clean up verse text for natural TTS recitation."""
    text = sanskrit.strip()
    # Double danda → single for pause
    text = text.replace('॥', '।')
    # Remove Devanagari digits (verse numbers)
    text = re.sub(r'[०-९]+', '', text)
    # Newlines → sentence breaks
    text = text.replace('\n', '। ')
    # Clean up
    text = re.sub(r'।\s*।', '।', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # ॐ → ओम्, (with comma pause) so TTS says "Om" not "A-U-M"
    text = text.replace('ॐ', 'ओम्,')
    # Fix Sanskrit schwa deletion
    text = add_schwa_hints(text)
    return text


def generate_audio(text, output_path):
    """Call ElevenLabs API and save MP3."""
    payload = json.dumps({
        'text': text,
        'model_id': 'eleven_multilingual_v2',
        'voice_settings': {
            'stability': 0.6,
            'similarity_boost': 0.8,
            'speed': 0.9,
        },
    }).encode('utf-8')

    req = urllib.request.Request(
        ELEVENLABS_URL,
        data=payload,
        headers={
            'xi-api-key': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'audio/mpeg',
        },
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        audio = resp.read()

    with open(output_path, 'wb') as f:
        f.write(audio)

    return len(audio)


def main():
    if not API_KEY:
        print('ERROR: ELEVENLAB_API_KEY not found in .env.local', file=sys.stderr)
        sys.exit(1)

    os.makedirs(AUDIO_DIR, exist_ok=True)

    target_sk = None
    target_ch = None
    force = '--force' in sys.argv

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--skandha' and i < len(sys.argv) - 1:
            target_sk = int(sys.argv[i + 1])
        if '-' in arg and arg[0].isdigit():
            parts = arg.split('-')
            target_sk, target_ch = int(parts[0]), int(parts[1])

    # Collect lessons
    lessons = []
    for f in sorted(os.listdir(LESSON_DIR)):
        if not f.endswith('.json'):
            continue
        ch_id = f.replace('.json', '')
        parts = ch_id.split('-')
        if len(parts) != 2:
            continue
        sk, ch = int(parts[0]), int(parts[1])
        if target_sk and sk != target_sk:
            continue
        if target_ch and ch != target_ch:
            continue
        lessons.append((ch_id, sk, ch))

    print(f'Generating ElevenLabs audio for {len(lessons)} chapters...')
    print(f'  Voice: Rachel | Model: eleven_multilingual_v2 | Speed: 0.9')
    print(f'  Output: {AUDIO_DIR}')
    print()

    generated = 0
    skipped = 0
    failed = 0

    for i, (ch_id, sk, ch) in enumerate(lessons):
        output_path = os.path.join(AUDIO_DIR, f'{ch_id}.mp3')

        if os.path.exists(output_path) and not force:
            skipped += 1
            continue

        # Load lesson
        with open(os.path.join(LESSON_DIR, f'{ch_id}.json'), 'r', encoding='utf-8') as f:
            lesson = json.load(f)

        sanskrit = lesson.get('verse', {}).get('sanskrit', '')
        if not sanskrit or len(sanskrit) < 10:
            print(f'  [{i+1}/{len(lessons)}] {ch_id} — no Sanskrit verse, skipping')
            failed += 1
            continue

        text = prepare_verse_text(sanskrit)
        print(f'  [{i+1}/{len(lessons)}] {ch_id} ({len(text)} chars)', end=' ', flush=True)

        try:
            size = generate_audio(text, output_path)
            print(f'— ✓ {size // 1024}KB')
            generated += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:200]
            print(f'— ✗ HTTP {e.code}: {body}')
            failed += 1
            if e.code == 429:
                print('    Rate limited, waiting 60s...')
                time.sleep(60)
        except Exception as e:
            print(f'— ✗ {e}')
            failed += 1

        # ElevenLabs rate limit: ~2-3 req/s for paid plans
        time.sleep(1.0)

    print(f'\n{"="*60}')
    print(f'DONE: {generated} generated, {skipped} cached, {failed} failed')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
