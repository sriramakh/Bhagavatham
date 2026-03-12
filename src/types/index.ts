export interface SanskritWord {
  san: string;          // Devanagari
  trans: string;        // IAST transliteration
  mean: string;         // English meaning
  full: string;         // Detailed explanation
  example?: string;     // Usage example
}

export interface Verse {
  ref: string;          // e.g. "1.1.1"
  sanskrit: string;     // Full Devanagari text
  transliteration: string;
  translation: string;
  syllables: string[];
  words: SanskritWord[];
  imagePath?: string;   // Path to generated image
}

export interface StoryBeat {
  type: 'narration' | 'dialogue';
  speaker?: string;
  text: string;
}

export interface QuizQuestion {
  type: 'mcq' | 'fill' | 'match';
  question: string;
  options?: string[];
  correct?: number;
  answer?: string;
  pairs?: [string, string][];
  explanation: string;
}

export interface Chapter {
  id: string;           // e.g. "1-1"
  skandha: number;
  num: number;
  title: string;
  desc: string;
  status?: string;      // 'coming_soon' for stub chapters
  story: StoryBeat[];
  verse: Verse;
  madhvaTeaching: string;
  sanskritWords: SanskritWord[];
  quiz: QuizQuestion[];
  boss: QuizQuestion[];
}

export interface Character {
  id: string;
  name: string;
  nameDevanagari: string;
  description: string;       // For narrative
  visualDescription: string; // Detailed physical for image gen consistency
  role: string;
}

export interface GameState {
  xp: number;
  level: number;
  hearts: number;
  maxHearts: number;
  streak: number;
  lastPlayDate: string | null;
  badges: string[];
  learnedWords: SanskritWord[];
  completedChapters: string[];
  currentSkandha: number;
  currentChapter: string | null;
  currentStep: number;
  totalCorrect: number;
  totalAnswered: number;
  versesStudied: number;
  quizzesCompleted: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export const LEVELS = [
  { name: 'Seeker', xpNeeded: 0 },
  { name: 'Student', xpNeeded: 100 },
  { name: 'Scholar', xpNeeded: 300 },
  { name: 'Pandita', xpNeeded: 600 },
  { name: 'Acharya', xpNeeded: 1000 },
] as const;

export const SKANDHA_NAMES = [
  'Creation', 'Divine Appearance', 'Status Quo', 'Fourth', 'Creative Impetus',
  'Prescribed Duties', 'Science of God', 'Withdrawal', 'Liberation',
  'The Summum Bonum', 'General History', 'The Age of Deterioration'
] as const;
