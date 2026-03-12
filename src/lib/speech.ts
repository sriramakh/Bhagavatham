/**
 * Sanskrit speech utilities — ElevenLabs Rachel voice.
 *
 * Full verses: served from pre-generated static files at /audio/verses/{chapterId}.mp3
 * Words/syllables: generated on-demand via /api/tts (cached after first call)
 * Fallback: Web Speech API hi-IN if everything else fails
 */

// --- Audio playback ---
let currentAudio: HTMLAudioElement | null = null;

// --- In-flight request dedup ---
const pendingRequests = new Map<string, Promise<string | null>>();

/**
 * Check if a static audio file exists by trying to load it.
 * Returns the URL if it loads, null otherwise.
 */
async function checkStaticAudio(url: string): Promise<string | null> {
  try {
    const res = await fetch(url, { method: 'HEAD' });
    return res.ok ? url : null;
  } catch {
    return null;
  }
}

/**
 * Request TTS audio from the API. Deduplicates concurrent requests.
 */
async function fetchTTSAudio(
  text: string,
  mode: 'verse' | 'word' | 'syllable' = 'word'
): Promise<string | null> {
  const key = `${text}|${mode}`;

  if (pendingRequests.has(key)) {
    return pendingRequests.get(key)!;
  }

  const promise = (async () => {
    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, mode }),
      });
      if (!res.ok) return null;
      const data = await res.json();
      return data.url as string | null;
    } catch {
      return null;
    } finally {
      pendingRequests.delete(key);
    }
  })();

  pendingRequests.set(key, promise);
  return promise;
}

/**
 * Play audio from a URL. Stops any currently playing audio first.
 */
function playAudioUrl(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    stopSpeech();
    const audio = new Audio(url);
    currentAudio = audio;
    audio.onended = () => {
      currentAudio = null;
      resolve();
    };
    audio.onerror = () => {
      currentAudio = null;
      reject(new Error('Audio playback failed'));
    };
    audio.play().catch(reject);
  });
}

// --- Web Speech API fallback ---
let voicesLoaded = false;

function ensureVoices(): void {
  if (voicesLoaded) return;
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => {
      voicesLoaded = true;
    };
  }
}

function fallbackWebSpeech(text: string, rate: number = 0.8): void {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

  ensureVoices();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'hi-IN';
  utterance.rate = rate;
  utterance.pitch = 1.0;

  const voices = window.speechSynthesis.getVoices();
  const hindiVoice =
    voices.find((v) => v.lang.startsWith('hi')) ||
    voices.find((v) => v.lang.startsWith('sa')) ||
    voices[0];
  if (hindiVoice) utterance.voice = hindiVoice;

  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

// --- Public API ---

/**
 * Play the pre-generated verse audio for a chapter.
 * Falls back to on-demand TTS, then Web Speech.
 *
 * @param chapterId - e.g. "1-1" for Skandha 1, Chapter 1
 * @param verseSanskrit - full Sanskrit text (used for fallback)
 */
export async function speakVerse(
  chapterId: string,
  verseSanskrit: string,
  slow: boolean = false
): Promise<void> {
  if (typeof window === 'undefined') return;
  stopSpeech();

  // 1. Try pre-generated static file
  const staticUrl = `/audio/verses/${chapterId}.mp3`;
  const exists = await checkStaticAudio(staticUrl);
  if (exists) {
    try {
      // For slow mode, use playback rate on the audio element
      if (slow) {
        return new Promise((resolve, reject) => {
          stopSpeech();
          const audio = new Audio(staticUrl);
          audio.playbackRate = 0.7;
          currentAudio = audio;
          audio.onended = () => { currentAudio = null; resolve(); };
          audio.onerror = () => { currentAudio = null; reject(); };
          audio.play().catch(reject);
        });
      }
      await playAudioUrl(staticUrl);
      return;
    } catch { /* fall through */ }
  }

  // 2. Try on-demand ElevenLabs via API
  const url = await fetchTTSAudio(verseSanskrit, 'verse');
  if (url) {
    try {
      await playAudioUrl(url);
      return;
    } catch { /* fall through */ }
  }

  // 3. Web Speech fallback
  fallbackWebSpeech(verseSanskrit, slow ? 0.5 : 0.8);
}

/**
 * Speak a single word clearly via ElevenLabs.
 */
export async function speakWord(text: string): Promise<void> {
  if (typeof window === 'undefined') return;
  stopSpeech();

  const url = await fetchTTSAudio(text, 'word');
  if (url) {
    try { await playAudioUrl(url); return; } catch { /* fall through */ }
  }
  fallbackWebSpeech(text, 0.7);
}

/**
 * Speak a single syllable slowly via ElevenLabs.
 */
export async function speakSyllable(text: string): Promise<void> {
  if (typeof window === 'undefined') return;
  stopSpeech();

  const url = await fetchTTSAudio(text, 'syllable');
  if (url) {
    try { await playAudioUrl(url); return; } catch { /* fall through */ }
  }
  fallbackWebSpeech(text, 0.7);
}

/**
 * Stop all audio playback.
 */
export function stopSpeech(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
}
