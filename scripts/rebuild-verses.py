#!/usr/bin/env python3
"""Rebuild verses.json from cached lessons + stubs for missing chapters."""
import json, os, re, fitz

SCRIPT_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')
VERSES_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'verses.json')
PDF_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'srimad-bhagavata-mahapurana-english-translations.pdf')

SKANDHA_INFO = {
    1: {"name": "Creation", "nameDevanagari": "सृष्टि", "desc": "The first canto introduces the purpose of the Bhagavatam and the fundamental questions of existence."},
    2: {"name": "The Cosmic Manifestation", "nameDevanagari": "विश्वरचना", "desc": "Describes the cosmic form of the Lord, creation, and the science of God-realization."},
    3: {"name": "The Status Quo", "nameDevanagari": "यथास्थिति", "desc": "Vidura's pilgrimage, creation by Vishnu, appearance of Lord Kapila, and His teachings to Devahuti."},
    4: {"name": "The Creation of the Fourth Order", "nameDevanagari": "चतुर्थ सृष्टि", "desc": "Stories of Dhruva, Prithu, Daksha, and the importance of devotion over ritual."},
    5: {"name": "The Creative Impetus", "nameDevanagari": "सृष्टि प्रेरणा", "desc": "Description of the universe's structure, the story of Rishabhadeva and King Bharata."},
    6: {"name": "Prescribed Duties", "nameDevanagari": "विहित कर्म", "desc": "The story of Ajamila, Daksha's prayers, Indra vs Vritrasura, and the power of the holy name."},
    7: {"name": "The Science of God", "nameDevanagari": "ईश्वर विज्ञान", "desc": "The story of Prahlada and Narasimha, and detailed teachings on devotional service."},
    8: {"name": "Withdrawal of the Cosmic Creations", "nameDevanagari": "सृष्टि प्रत्याहार", "desc": "The Gajendra-moksha, churning of the ocean, Vamana avatar, and the Manu dynasties."},
    9: {"name": "Liberation", "nameDevanagari": "मुक्ति", "desc": "The dynasties of the Sun and Moon, stories of Lord Ramachandra and other incarnations."},
    10: {"name": "The Summum Bonum", "nameDevanagari": "परम तत्त्व", "desc": "The complete pastimes of Lord Krishna — His birth, childhood, youth, and divine activities."},
    11: {"name": "General History", "nameDevanagari": "सामान्य इतिहास", "desc": "Krishna's final teachings (Uddhava Gita), the destruction of the Yadu dynasty, and the Lord's departure."},
    12: {"name": "The Age of Deterioration", "nameDevanagari": "कलियुग", "desc": "The age of Kali, the future avatars, the essence of all Puranas, and the glory of the Bhagavatam."},
}

# Extract chapters from PDF
doc = fitz.open(PDF_PATH)
full_text = ""
for i in range(len(doc)):
    full_text += doc[i].get_text() + "\n"

sb_pattern = re.compile(r'SB\s+(\d+)\.(\d+):\s*(.+?)(?:\n|$)')
chapters = []
for match in sb_pattern.finditer(full_text):
    chapters.append({
        "skandha": int(match.group(1)),
        "chapter": int(match.group(2)),
        "title": match.group(3).strip()
    })
print(f"Extracted {len(chapters)} chapters from PDF")

# Load cached lessons
cached = {}
for fname in os.listdir(CACHE_DIR):
    if fname.endswith('.json'):
        ch_id = fname.replace('.json', '')
        with open(os.path.join(CACHE_DIR, fname)) as f:
            cached[ch_id] = json.load(f)
print(f"Cached lessons: {len(cached)}")

# Build
skandhas = []
for sk_num in range(1, 13):
    info = SKANDHA_INFO[sk_num]
    sk_chapters = sorted([c for c in chapters if c['skandha'] == sk_num], key=lambda c: c['chapter'])
    chapter_data = []
    for ch_info in sk_chapters:
        ch_id = f"{sk_num}-{ch_info['chapter']}"
        if ch_id in cached:
            chapter_data.append(cached[ch_id])
        else:
            chapter_data.append({
                "id": ch_id, "skandha": sk_num, "num": ch_info['chapter'],
                "title": ch_info['title'],
                "desc": f"Chapter {ch_info['chapter']} of Skandha {sk_num}.",
                "status": "coming_soon"
            })
    skandhas.append({
        "number": sk_num, "name": info["name"],
        "nameDevanagari": info["nameDevanagari"],
        "description": info["desc"], "chapters": chapter_data
    })

result = {"skandhas": skandhas}
with open(VERSES_PATH, 'w') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

ready = 0
stubs = 0
for sk in skandhas:
    r = len([c for c in sk['chapters'] if c.get('status') != 'coming_soon'])
    s = len([c for c in sk['chapters'] if c.get('status') == 'coming_soon'])
    ready += r
    stubs += s
    print(f"  Skandha {sk['number']:2d}: {r} ready, {s} stubs")

print(f"\nTotal: {ready} ready, {stubs} stubs, {ready + stubs} chapters")
print(f"Saved to: {VERSES_PATH}")
