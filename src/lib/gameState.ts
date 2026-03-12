import { GameState, LEVELS } from '@/types';

const STORAGE_KEY = 'bhagavatam_quest_state';

export const DEFAULT_STATE: GameState = {
  xp: 0,
  level: 0,
  hearts: 3,
  maxHearts: 3,
  streak: 0,
  lastPlayDate: null,
  badges: [],
  learnedWords: [],
  completedChapters: [],
  currentSkandha: 1,
  currentChapter: null,
  currentStep: 0,
  totalCorrect: 0,
  totalAnswered: 0,
  versesStudied: 0,
  quizzesCompleted: 0,
};

export function loadGameState(): GameState {
  if (typeof window === 'undefined') return { ...DEFAULT_STATE };
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return { ...DEFAULT_STATE, ...JSON.parse(saved) };
    }
  } catch {
    // ignore corrupt data
  }
  return { ...DEFAULT_STATE };
}

export function saveGameState(state: GameState): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore storage full
  }
}

export function resetGameState(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(STORAGE_KEY);
}

export function getLevel(xp: number): number {
  let lvl = 0;
  for (let i = LEVELS.length - 1; i >= 0; i--) {
    if (xp >= LEVELS[i].xpNeeded) {
      lvl = i;
      break;
    }
  }
  return lvl;
}

export function getLevelProgress(xp: number) {
  const lvl = getLevel(xp);
  const nextLevel = lvl < LEVELS.length - 1 ? LEVELS[lvl + 1] : null;
  const xpInLevel = xp - LEVELS[lvl].xpNeeded;
  const xpForNext = nextLevel ? nextLevel.xpNeeded - LEVELS[lvl].xpNeeded : 1;
  const pct = nextLevel ? Math.min(100, (xpInLevel / xpForNext) * 100) : 100;
  return {
    level: lvl,
    levelName: LEVELS[lvl].name,
    xpInLevel,
    xpForNext,
    pct,
    isMax: !nextLevel,
  };
}

export function checkStreak(state: GameState): GameState {
  const today = new Date().toISOString().split('T')[0];
  const newState = { ...state };
  if (state.lastPlayDate) {
    const last = new Date(state.lastPlayDate);
    const now = new Date(today);
    const diff = Math.floor((now.getTime() - last.getTime()) / 86400000);
    if (diff > 1) newState.streak = 0;
    else if (diff === 1) newState.streak++;
  } else {
    newState.streak = 1;
  }
  newState.lastPlayDate = today;
  return newState;
}

export function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function toRoman(n: number): string {
  const romans = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'];
  return romans[n - 1] || String(n);
}
