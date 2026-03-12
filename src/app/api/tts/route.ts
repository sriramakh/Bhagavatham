import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

const AUDIO_DIR = path.join(process.cwd(), 'public', 'audio');
const ELEVENLABS_API_URL = 'https://api.elevenlabs.io/v1/text-to-speech';
const RACHEL_VOICE_ID = '21m00Tcm4TlvDq8ikWAM';

/**
 * Generate natural Sanskrit speech using ElevenLabs TTS.
 * Voice: Rachel (multilingual v2), speed 0.9
 *
 * POST /api/tts
 * Body: { text: string, mode?: "verse" | "word" | "syllable" }
 *
 * Audio is cached to public/audio/ — each unique text generated once.
 */
export async function POST(req: NextRequest) {
  try {
    const { text, mode = 'word' } = await req.json();

    if (!text || typeof text !== 'string') {
      return NextResponse.json({ error: 'text is required' }, { status: 400 });
    }

    const apiKey = process.env.ELEVENLAB_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: 'ELEVENLAB_API_KEY not configured' },
        { status: 500 }
      );
    }

    // Cache key
    const cacheKey = crypto
      .createHash('md5')
      .update(`eleven|${text}|${mode}`)
      .digest('hex');

    const subDir = mode === 'verse' ? 'verses' : 'words';
    const cacheDir = path.join(AUDIO_DIR, subDir);
    const cachePath = path.join(cacheDir, `${cacheKey}.mp3`);
    const publicUrl = `/audio/${subDir}/${cacheKey}.mp3`;

    // Return cached audio if exists
    if (fs.existsSync(cachePath)) {
      return NextResponse.json({ url: publicUrl });
    }

    // Prepare text for better verse recitation
    let processedText = text.trim();

    if (mode === 'verse') {
      // Replace double danda with period for natural full-stop pause
      processedText = processedText.replace(/॥/g, '।');
      // Remove verse numbers (Devanagari digits)
      processedText = processedText.replace(/[०-९]+/g, '');
      // Newlines to sentence breaks
      processedText = processedText.replace(/\n+/g, '। ');
      // Clean up
      processedText = processedText.replace(/।\s*।/g, '।');
      processedText = processedText.replace(/\s+/g, ' ').trim();
    }

    // Speed: 0.9 for verses (slightly slower for clarity), 0.85 for syllables, 0.9 for words
    const speed = mode === 'syllable' ? 0.85 : 0.9;

    const response = await fetch(`${ELEVENLABS_API_URL}/${RACHEL_VOICE_ID}`, {
      method: 'POST',
      headers: {
        'xi-api-key': apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: processedText,
        model_id: 'eleven_multilingual_v2',
        voice_settings: {
          stability: 0.6,
          similarity_boost: 0.8,
          speed,
        },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('ElevenLabs TTS error:', response.status, errorText);
      return NextResponse.json(
        { error: `ElevenLabs API error: ${response.status}` },
        { status: 502 }
      );
    }

    // ElevenLabs returns raw audio bytes directly
    const audioBuffer = Buffer.from(await response.arrayBuffer());

    // Cache
    fs.mkdirSync(cacheDir, { recursive: true });
    fs.writeFileSync(cachePath, audioBuffer);

    return NextResponse.json({ url: publicUrl });
  } catch (error: any) {
    console.error('TTS error:', error);
    return NextResponse.json(
      { error: error.message || 'TTS generation failed' },
      { status: 500 }
    );
  }
}
