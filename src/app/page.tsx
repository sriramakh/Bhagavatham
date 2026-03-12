'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Chapter, GameState, SKANDHA_NAMES } from '@/types';
import {
  DEFAULT_STATE,
  loadGameState,
  saveGameState,
  resetGameState,
  getLevelProgress,
  checkStreak,
  toRoman,
} from '@/lib/gameState';
import { showToast } from '@/components/Toast';

import TopBar from '@/components/TopBar';
import CharacterPanel from '@/components/CharacterPanel';
import WordBank from '@/components/WordBank';
import StoryMode from '@/components/StoryMode';
import VerseStudy from '@/components/VerseStudy';
import SanskritLesson from '@/components/SanskritLesson';
import QuizBattle from '@/components/QuizBattle';
import ChatPanel from '@/components/ChatPanel';
import SettingsModal from '@/components/SettingsModal';
import ToastContainer from '@/components/Toast';

type Screen =
  | 'welcome'
  | 'chapterSelect'
  | 'story'
  | 'verse'
  | 'sanskrit'
  | 'quiz'
  | 'boss'
  | 'results';

export default function Home() {
  const [state, setState] = useState<GameState>(DEFAULT_STATE);
  const [screen, setScreen] = useState<Screen>('welcome');
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentChapter, setCurrentChapter] = useState<Chapter | null>(null);
  const [chapterProgress, setChapterProgress] = useState<Record<string, boolean[]>>({});
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [bossStarted, setBossStarted] = useState(false);
  const [quizResults, setQuizResults] = useState<{
    correct: number;
    total: number;
    xpEarned: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize state from localStorage
  useEffect(() => {
    const saved = loadGameState();
    const withStreak = checkStreak(saved);
    setState(withStreak);
    saveGameState(withStreak);
    setLoading(false);
  }, []);

  // Fetch chapters for current skandha
  useEffect(() => {
    if (loading) return;
    fetchChapters(state.currentSkandha);
  }, [state.currentSkandha, loading]);

  const fetchChapters = async (skandha: number) => {
    try {
      const res = await fetch(`/api/verses?skandha=${skandha}`);
      const data = await res.json();
      if (data.chapters) {
        setChapters(data.chapters);
      } else if (data.error) {
        console.error('Failed to fetch chapters:', data.error);
        setChapters([]);
      }
    } catch {
      console.error('Failed to fetch chapters');
      setChapters([]);
    }
  };

  // Save state whenever it changes
  useEffect(() => {
    if (!loading) {
      saveGameState(state);
    }
  }, [state, loading]);

  const levelInfo = useMemo(() => getLevelProgress(state.xp), [state.xp]);

  // Progress percentage for top bar
  const topProgress = useMemo(() => {
    if (chapters.length === 0) return 0;
    const completed = state.completedChapters.filter((c) =>
      c.startsWith(`${state.currentSkandha}-`)
    ).length;
    return Math.round((completed / chapters.length) * 100);
  }, [chapters, state.completedChapters, state.currentSkandha]);

  // Mutation helpers
  const addXP = useCallback(
    (amount: number) => {
      setState((prev) => {
        const newXP = prev.xp + amount;
        const oldLevel = getLevelProgress(prev.xp).level;
        const newLevel = getLevelProgress(newXP).level;
        if (newLevel > oldLevel && oldLevel > 0) {
          setTimeout(() => {
            const name = getLevelProgress(newXP).levelName;
            showToast(`Level Up! You are now a ${name}!`, 'badge');
          }, 500);
        }
        return { ...prev, xp: newXP };
      });
    },
    []
  );

  const earnBadge = useCallback((id: string, name: string) => {
    setState((prev) => {
      if (prev.badges.includes(id)) return prev;
      showToast(`Badge earned: ${name}`, 'badge');
      return { ...prev, badges: [...prev.badges, id] };
    });
  }, []);

  const loseHeart = useCallback(() => {
    setState((prev) => {
      if (prev.hearts <= 0) {
        showToast('No hearts left! Answers still accepted.', 'heart');
        return prev;
      }
      const newHearts = prev.hearts - 1;
      showToast(`Heart lost! ${newHearts} remaining`, 'heart');
      return { ...prev, hearts: newHearts };
    });
  }, []);

  // Navigation
  const goToChapterSelect = useCallback(() => {
    setScreen('chapterSelect');
  }, []);

  const selectSkandha = useCallback((num: number) => {
    setState((prev) => ({ ...prev, currentSkandha: num }));
    setScreen('chapterSelect');
  }, []);

  const startChapter = useCallback(
    (chapter: Chapter) => {
      setCurrentChapter(chapter);
      setState((prev) => ({
        ...prev,
        hearts: prev.maxHearts,
        currentChapter: chapter.id,
        currentStep: 0,
      }));
      if (!chapterProgress[chapter.id]) {
        setChapterProgress((prev) => ({
          ...prev,
          [chapter.id]: [false, false, false, false, false],
        }));
      }
      setScreen('story');
      setBossStarted(false);
      setQuizResults(null);

      // XP for reading story
      addXP(10);
      showToast('+10 XP — Story read!', 'xp');
    },
    [chapterProgress, addXP]
  );

  const advanceStep = useCallback(() => {
    if (!currentChapter) return;
    setChapterProgress((prev) => {
      const steps = [...(prev[currentChapter.id] || [false, false, false, false, false])];
      const stepMap: Record<Screen, number> = {
        story: 0,
        verse: 1,
        sanskrit: 2,
        quiz: 3,
        boss: 4,
        welcome: -1,
        chapterSelect: -1,
        results: -1,
      };
      const idx = stepMap[screen];
      if (idx >= 0) steps[idx] = true;
      return { ...prev, [currentChapter.id]: steps };
    });

    const nextScreenMap: Record<string, Screen> = {
      story: 'verse',
      verse: 'sanskrit',
      sanskrit: 'quiz',
      quiz: 'boss',
    };
    const next = nextScreenMap[screen];
    if (next) {
      setScreen(next);
      // XP for verse study
      if (screen === 'story') {
        setState((prev) => ({
          ...prev,
          versesStudied: prev.versesStudied + 1,
          currentStep: 1,
        }));
        addXP(15);
        showToast('+15 XP — Verse studied!', 'xp');
        if (!state.badges.includes('first-verse')) {
          earnBadge('first-verse', 'First Verse');
        }
      }
      // XP for sanskrit lesson
      if (screen === 'verse') {
        setState((prev) => ({ ...prev, currentStep: 2 }));
        // Learn words
        if (currentChapter.sanskritWords) {
          setState((prev) => {
            const newWords = [...prev.learnedWords];
            currentChapter.sanskritWords.forEach((w) => {
              if (!newWords.find((lw) => lw.san === w.san)) {
                newWords.push({ san: w.san, trans: w.trans, mean: w.mean, full: w.full || w.mean });
              }
            });
            const updated = { ...prev, learnedWords: newWords };
            if (!prev.badges.includes('sanskrit-novice') && newWords.length >= 5) {
              earnBadge('sanskrit-novice', 'Sanskrit Novice');
            }
            return updated;
          });
          addXP(10);
          showToast('+10 XP — Sanskrit words learned!', 'xp');
        }
      }
      if (screen === 'sanskrit') {
        setState((prev) => ({ ...prev, currentStep: 3 }));
      }
      if (screen === 'quiz') {
        setState((prev) => ({ ...prev, currentStep: 4 }));
        setBossStarted(false);
      }
    }
  }, [currentChapter, screen, state.badges, addXP, earnBadge]);

  const goBackStep = useCallback(() => {
    const prevMap: Record<string, Screen> = {
      verse: 'story',
      sanskrit: 'verse',
      quiz: 'sanskrit',
      boss: 'quiz',
      story: 'chapterSelect',
    };
    const prev = prevMap[screen];
    if (prev) setScreen(prev);
  }, [screen]);

  // Quiz completion
  const handleQuizComplete = useCallback(
    (correct: number, total: number) => {
      setState((prev) => ({
        ...prev,
        quizzesCompleted: prev.quizzesCompleted + 1,
      }));
      if (!state.badges.includes('quiz-warrior')) {
        earnBadge('quiz-warrior', 'Quiz Warrior');
      }
      if (correct === total && !state.badges.includes('perfect-quiz')) {
        earnBadge('perfect-quiz', 'Perfect Score');
      }
      addXP(20);
      showToast('+20 XP — Quiz complete!', 'xp');
      advanceStep();
    },
    [state.badges, addXP, earnBadge, advanceStep]
  );

  // Boss completion
  const handleBossComplete = useCallback(
    (correct: number, total: number) => {
      if (!currentChapter) return;

      setState((prev) => {
        const newState = { ...prev, quizzesCompleted: prev.quizzesCompleted + 1 };
        if (!prev.completedChapters.includes(currentChapter.id)) {
          newState.completedChapters = [...prev.completedChapters, currentChapter.id];
        }
        return newState;
      });

      setChapterProgress((prev) => ({
        ...prev,
        [currentChapter.id]: [true, true, true, true, true],
      }));

      if (!state.badges.includes('boss-slayer')) earnBadge('boss-slayer', 'Boss Slayer');
      if (!state.badges.includes('madhva-disciple'))
        earnBadge('madhva-disciple', "Madhva's Disciple");
      if (!state.badges.includes('chapter-complete'))
        earnBadge('chapter-complete', 'Chapter Master');

      const xpEarned = 50;
      addXP(xpEarned);

      if (state.streak >= 3 && !state.badges.includes('streak-3')) {
        earnBadge('streak-3', '3-Day Streak');
      }

      setQuizResults({ correct, total, xpEarned });
      setScreen('results');
    },
    [currentChapter, state.badges, state.streak, addXP, earnBadge]
  );

  const handleQuizCorrect = useCallback(() => {
    addXP(5);
    setState((prev) => ({
      ...prev,
      totalCorrect: prev.totalCorrect + 1,
      totalAnswered: prev.totalAnswered + 1,
    }));
  }, [addXP]);

  const handleQuizWrong = useCallback(() => {
    setState((prev) => ({ ...prev, totalAnswered: prev.totalAnswered + 1 }));
    loseHeart();
  }, [loseHeart]);

  // Settings
  const handleResetProgress = useCallback(() => {
    resetGameState();
    setState({ ...DEFAULT_STATE });
    setScreen('welcome');
    setCurrentChapter(null);
    setChapterProgress({});
    setSettingsOpen(false);
    showToast('Progress reset', 'success');
  }, []);

  const handleToggleSound = useCallback((enabled: boolean) => {
    setState((prev) => ({ ...prev }));
    // Sound toggle stored but Web Speech API doesn't need a global mute
  }, []);

  // Chat context
  const chatContext = useMemo(() => {
    if (!currentChapter) return null;
    return {
      verse: currentChapter.verse,
      madhvaTeaching: currentChapter.madhvaTeaching,
      chapterTitle: currentChapter.title,
    };
  }, [currentChapter]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a12]">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full border-[3px] border-[#d4a843] flex items-center justify-center text-3xl animate-pulse-gold">
            {'\uD83D\uDE4F'}
          </div>
          <div className="font-heading text-[#d4a843] tracking-[2px]">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <>
      <ToastContainer />

      <TopBar
        skandha={`Skandha ${toRoman(state.currentSkandha)}`}
        chapter={currentChapter?.title || SKANDHA_NAMES[state.currentSkandha - 1]}
        progress={topProgress}
        streak={state.streak}
        hearts={state.hearts}
        maxHearts={state.maxHearts}
        onSettingsClick={() => setSettingsOpen(true)}
      />

      <div className="grid grid-cols-[260px_1fr_240px] gap-0 mt-14 min-h-[calc(100vh-56px)] max-lg:grid-cols-[1fr] max-xl:grid-cols-[220px_1fr_200px]">
        {/* Left Sidebar */}
        <div className="max-lg:hidden">
          <CharacterPanel state={state} onSelectSkandha={selectSkandha} />
        </div>

        {/* Main Content */}
        <main className="px-8 py-6 max-w-full overflow-y-auto h-[calc(100vh-56px)]">
          {/* Welcome Screen */}
          {screen === 'welcome' && (
            <WelcomeScreen onStart={goToChapterSelect} onReset={handleResetProgress} />
          )}

          {/* Chapter Select */}
          {screen === 'chapterSelect' && (
            <ChapterSelectScreen
              skandha={state.currentSkandha}
              chapters={chapters}
              completedChapters={state.completedChapters}
              chapterProgress={chapterProgress}
              onSelectChapter={startChapter}
              onSelectSkandha={selectSkandha}
              onBack={() => setScreen('welcome')}
            />
          )}

          {/* In-chapter screens with step tabs */}
          {currentChapter && ['story', 'verse', 'sanskrit', 'quiz', 'boss', 'results'].includes(screen) && (
            <>
              {/* Step Navigation Tabs */}
              {screen !== 'results' && (
                <div className="mb-5">
                  <div className="flex items-center gap-2 mb-3">
                    <button
                      onClick={goToChapterSelect}
                      className="text-[0.75rem] text-[#a89b8c] hover:text-[#d4a843] transition-colors cursor-pointer bg-transparent border-none"
                    >
                      {'\u2190'} Chapters
                    </button>
                    <span className="text-[#2a2a3e]">|</span>
                    <span className="text-[0.75rem] text-[#6b6157]">
                      Skandha {state.currentSkandha} {'\u00B7'} Ch. {currentChapter.num}: {currentChapter.title}
                    </span>
                  </div>
                  <div className="flex gap-1">
                    {([
                      { key: 'story' as Screen, label: 'Story', icon: '\uD83D\uDCDC' },
                      { key: 'verse' as Screen, label: 'Verse', icon: '\uD83D\uDD49\uFE0F' },
                      { key: 'sanskrit' as Screen, label: 'Sanskrit', icon: '\uD83D\uDCDA' },
                      { key: 'quiz' as Screen, label: 'Quiz', icon: '\u2694\uFE0F' },
                      { key: 'boss' as Screen, label: 'Boss', icon: '\uD83D\uDC09' },
                    ]).map((tab) => (
                      <button
                        key={tab.key}
                        onClick={() => {
                          setScreen(tab.key);
                          if (tab.key === 'boss') setBossStarted(false);
                        }}
                        className={`px-3 py-1.5 rounded-lg text-[0.75rem] font-heading tracking-[0.5px] transition-all cursor-pointer border ${
                          screen === tab.key
                            ? 'bg-[#1a1a2e] text-[#d4a843] border-[#8a6d2b]'
                            : 'bg-transparent text-[#6b6157] border-transparent hover:text-[#a89b8c] hover:border-[#2a2a3e]'
                        }`}
                      >
                        {tab.icon} {tab.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Story */}
              {screen === 'story' && (
                <StoryMode
                  story={currentChapter.story}
                  chapterLabel={`Skandha ${state.currentSkandha} \u00B7 Chapter ${currentChapter.num}`}
                  title={currentChapter.title}
                  onContinue={advanceStep}
                  onBack={goToChapterSelect}
                />
              )}

              {/* Verse Study */}
              {screen === 'verse' && (
                <VerseStudy
                  verse={currentChapter.verse}
                  madhvaTeaching={currentChapter.madhvaTeaching}
                  chapterLabel={`Skandha ${state.currentSkandha} \u00B7 Chapter ${currentChapter.num}`}
                  chapterId={currentChapter.id}
                  chapterTitle={currentChapter.title}
                  onContinue={advanceStep}
                  onBack={goBackStep}
                />
              )}

              {/* Sanskrit Lesson */}
              {screen === 'sanskrit' && (
                <SanskritLesson
                  words={currentChapter.sanskritWords}
                  onContinue={advanceStep}
                  onBack={goBackStep}
                  onDndComplete={() => {
                    addXP(10);
                    showToast('+10 XP — Perfect matching!', 'xp');
                  }}
                  onDndError={loseHeart}
                />
              )}

              {/* Quiz */}
              {screen === 'quiz' && (
                <QuizBattle
                  questions={currentChapter.quiz}
                  title="Chapter Quiz"
                  subtitle={`${currentChapter.title} — Test your knowledge`}
                  onComplete={handleQuizComplete}
                  onCorrect={handleQuizCorrect}
                  onWrong={handleQuizWrong}
                />
              )}

              {/* Boss */}
              {screen === 'boss' && (
                <>
                  {!bossStarted ? (
                    <BossIntro onStart={() => setBossStarted(true)} />
                  ) : (
                    <QuizBattle
                      questions={currentChapter.boss}
                      title="Boss Challenge"
                      subtitle={currentChapter.title}
                      isBoss
                      onComplete={handleBossComplete}
                      onCorrect={handleQuizCorrect}
                      onWrong={handleQuizWrong}
                    />
                  )}
                </>
              )}

              {/* Results */}
              {screen === 'results' && quizResults && (
                <ResultsScreen
                  chapter={currentChapter}
                  correct={quizResults.correct}
                  total={quizResults.total}
                  xpEarned={quizResults.xpEarned}
                  hearts={state.hearts}
                  maxHearts={state.maxHearts}
                  onContinue={goToChapterSelect}
                  onReplay={() => startChapter(currentChapter)}
                />
              )}
            </>
          )}
        </main>

        {/* Right Sidebar */}
        <div className="max-lg:hidden">
          <WordBank words={state.learnedWords} />
        </div>
      </div>

      <ChatPanel verseContext={chatContext} isOpen={chatOpen} onToggle={() => setChatOpen((o) => !o)} />

      <SettingsModal
        isOpen={settingsOpen}
        soundEnabled={true}
        onClose={() => setSettingsOpen(false)}
        onResetProgress={handleResetProgress}
        onToggleSound={handleToggleSound}
      />
    </>
  );
}

// ========== Sub-screens ==========

function WelcomeScreen({ onStart, onReset }: { onStart: () => void; onReset: () => void }) {
  return (
    <div className="text-center py-10 px-5 animate-fadeIn">
      <div className="w-40 h-40 mx-auto mb-8 rounded-full border-[3px] border-[#d4a843] flex items-center justify-center text-[4rem] shadow-[0_0_20px_rgba(212,168,67,0.3),0_0_60px_rgba(212,168,67,0.1)] animate-pulse-gold bg-[radial-gradient(circle,rgba(212,168,67,0.1),transparent)]">
        {'\uD83D\uDE4F'}
      </div>
      <h1 className="font-heading text-[#d4a843] text-[2rem] tracking-[3px] mb-2">
        QUEST OF THE SKANDHAS
      </h1>
      <div className="font-sanskrit text-[#f4a03b] text-[1.3rem] mb-2">
        {'\u0936\u094D\u0930\u0940\u092E\u0926\u094D\u092D\u093E\u0917\u0935\u0924\u092E\u094D'}
      </div>
      <p className="text-[#a89b8c] max-w-[500px] mx-auto mb-8 text-[0.9rem] leading-[1.7]">
        Embark on a sacred journey through the 12 Skandhas of the Srimad Bhagavatam. As a Seeker,
        you will learn ancient Sanskrit, study divine verses, and discover the profound teachings of
        Madhvacharya. Each realm holds wisdom that will transform your understanding of the Supreme.
      </p>
      <button
        onClick={onStart}
        className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-br from-[#8a6d2b] to-[#d4a843] text-[#0a0a12] rounded-lg font-heading text-[0.9rem] tracking-[1px] shadow-[0_4px_15px_rgba(212,168,67,0.3)] hover:-translate-y-0.5 hover:shadow-[0_6px_25px_rgba(212,168,67,0.4)] active:translate-y-0 transition-all cursor-pointer"
      >
        Begin Your Quest {'\u2694\uFE0F'}
      </button>
      <div className="mt-4">
        <button
          onClick={onReset}
          className="text-[0.7rem] text-[#6b6157] opacity-50 bg-transparent border-none cursor-pointer hover:opacity-80 transition-opacity"
        >
          Reset Progress
        </button>
      </div>
    </div>
  );
}

function ChapterSelectScreen({
  skandha,
  chapters,
  completedChapters,
  chapterProgress,
  onSelectChapter,
  onSelectSkandha,
  onBack,
}: {
  skandha: number;
  chapters: Chapter[];
  completedChapters: string[];
  chapterProgress: Record<string, boolean[]>;
  onSelectChapter: (ch: Chapter) => void;
  onSelectSkandha: (num: number) => void;
  onBack: () => void;
}) {
  return (
    <div className="py-5 animate-fadeIn">
      {/* Skandha Tabs */}
      <div className="flex flex-wrap gap-1.5 mb-6 pb-4 border-b border-[#2a2a3e]">
        {SKANDHA_NAMES.map((name, i) => {
          const num = i + 1;
          const isActive = num === skandha;
          return (
            <button
              key={num}
              onClick={() => onSelectSkandha(num)}
              className={`px-3 py-1.5 rounded-lg text-[0.7rem] font-heading tracking-[0.5px] transition-all cursor-pointer border ${
                isActive
                  ? 'bg-gradient-to-br from-[#8a6d2b] to-[#d4a843] text-[#0a0a12] border-[#d4a843] shadow-[0_2px_10px_rgba(212,168,67,0.3)]'
                  : 'bg-transparent text-[#a89b8c] border-[#2a2a3e] hover:border-[#8a6d2b] hover:text-[#d4a843]'
              }`}
            >
              {toRoman(num)}. {name.length > 12 ? name.substring(0, 12) + '…' : name}
            </button>
          );
        })}
      </div>

      <h2 className="font-heading text-[#d4a843] text-[1.4rem] mb-1.5">
        Skandha {skandha} — {SKANDHA_NAMES[skandha - 1]}
      </h2>
      <p className="text-[#a89b8c] text-[0.85rem] mb-6">
        {skandha === 1
          ? 'The first canto introduces the purpose of the Bhagavatam and the fundamental questions of existence.'
          : `Explore the chapters of Skandha ${skandha}.`}
      </p>

      {chapters.length === 0 ? (
        <p className="text-[#6b6157] text-center py-10 italic">
          No chapters available yet for this skandha.
        </p>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4">
          {chapters.map((ch) => {
            const isCompleted = completedChapters.includes(ch.id);
            const isComingSoon = ch.status === 'coming_soon';
            const isLocked = isComingSoon;
            const steps = chapterProgress[ch.id] || [];

            return (
              <button
                key={ch.id}
                onClick={() => !isLocked && onSelectChapter(ch)}
                disabled={isLocked}
                className={`bg-[#1a1a2e] border rounded-xl p-5 text-left transition-all relative overflow-hidden group ${
                  isCompleted
                    ? 'border-[#27ae60] cursor-pointer'
                    : isLocked
                      ? 'border-[#2a2a3e] opacity-40 cursor-not-allowed'
                      : 'border-[#2a2a3e] cursor-pointer hover:border-[#8a6d2b] hover:-translate-y-[3px] hover:shadow-[0_4px_20px_rgba(0,0,0,0.4)]'
                }`}
              >
                {/* Top accent line */}
                <div
                  className={`absolute top-0 left-0 right-0 h-[3px] transition-opacity ${
                    isCompleted
                      ? 'bg-[#27ae60] opacity-100'
                      : 'bg-gradient-to-r from-[#8a6d2b] via-[#d4a843] to-[#8a6d2b] opacity-0 group-hover:opacity-100'
                  }`}
                />

                {isLocked && (
                  <div className="absolute top-4 right-4 text-[1.2rem] opacity-50">
                    {'\uD83D\uDD12'}
                  </div>
                )}
                {isCompleted && (
                  <div className="absolute top-4 right-4 text-[1.2rem]">
                    {'\u2705'}
                  </div>
                )}

                <div className="font-heading text-[#8a6d2b] text-[0.75rem] tracking-[1px] uppercase">
                  Chapter {ch.num}
                </div>
                <div className="font-heading text-[#e8e0d0] text-base my-1.5">{ch.title}</div>
                <div className="text-[#a89b8c] text-[0.8rem] leading-[1.5]">{ch.desc}</div>

                <div className="mt-3 flex items-center gap-2">
                  <div className="flex gap-1">
                    {[0, 1, 2, 3, 4].map((s) => (
                      <div
                        key={s}
                        className={`w-2 h-2 rounded-full border ${
                          steps[s]
                            ? 'bg-[#d4a843] border-[#d4a843]'
                            : 'bg-[#2a2a3e] border-[#6b6157]'
                        }`}
                      />
                    ))}
                  </div>
                  <span className="text-[0.7rem] text-[#6b6157]">
                    {isCompleted ? 'Completed' : isLocked ? 'Coming Soon' : 'Ready'}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      <div className="mt-5">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 px-5 py-2 border border-[#8a6d2b] text-[#f0d078] rounded-lg font-heading text-[0.8rem] tracking-[1px] bg-transparent hover:bg-[rgba(212,168,67,0.1)] hover:border-[#d4a843] transition-all cursor-pointer"
        >
          {'\u2190'} Back to Home
        </button>
      </div>
    </div>
  );
}

function BossIntro({ onStart }: { onStart: () => void }) {
  return (
    <div className="text-center py-10 animate-fadeIn">
      <div className="text-[4rem] mb-4">{'\uD83D\uDC09'}</div>
      <h2 className="font-heading text-[#c0392b] text-[1.5rem] tracking-[2px] mb-4">
        BOSS CHALLENGE
      </h2>
      <p className="text-[#a89b8c] max-w-[500px] mx-auto mb-8 text-[0.9rem] leading-[1.7]">
        Prove your mastery of this chapter with a comprehensive challenge. You must answer all
        questions correctly to complete the chapter!
      </p>
      <button
        onClick={onStart}
        className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-br from-[#8b0000] to-[#c0392b] text-white rounded-lg font-heading text-[0.9rem] tracking-[1px] shadow-[0_4px_15px_rgba(192,57,43,0.3)] hover:-translate-y-0.5 hover:shadow-[0_6px_25px_rgba(192,57,43,0.4)] active:translate-y-0 transition-all cursor-pointer"
      >
        Face the Challenge {'\u2694\uFE0F'}
      </button>
    </div>
  );
}

function ResultsScreen({
  chapter,
  correct,
  total,
  xpEarned,
  hearts,
  maxHearts,
  onContinue,
  onReplay,
}: {
  chapter: Chapter;
  correct: number;
  total: number;
  xpEarned: number;
  hearts: number;
  maxHearts: number;
  onContinue: () => void;
  onReplay: () => void;
}) {
  const accuracy = total > 0 ? Math.round((correct / total) * 100) : 0;

  return (
    <div className="text-center py-10 animate-fadeIn">
      <div className="text-[4rem] mb-4">{'\uD83C\uDFC6'}</div>
      <h2 className="font-heading text-[#d4a843] text-[1.5rem] tracking-[2px] mb-2">
        Chapter Complete!
      </h2>
      <p className="text-[#a89b8c] text-[0.9rem] mb-8">
        You have conquered &ldquo;{chapter.title}&rdquo;
      </p>

      <div className="flex justify-center gap-8 mb-8">
        <div className="text-center">
          <div className="font-heading text-[#f0d078] text-[1.5rem]">
            {correct}/{total}
          </div>
          <div className="text-[0.75rem] text-[#6b6157] uppercase">Correct</div>
        </div>
        <div className="text-center">
          <div className="font-heading text-[#f0d078] text-[1.5rem]">{accuracy}%</div>
          <div className="text-[0.75rem] text-[#6b6157] uppercase">Accuracy</div>
        </div>
        <div className="text-center">
          <div className="font-heading text-[#f0d078] text-[1.5rem]">
            {hearts}/{maxHearts}
          </div>
          <div className="text-[0.75rem] text-[#6b6157] uppercase">Hearts</div>
        </div>
      </div>

      <div className="text-[1.5rem] font-heading text-[#d4a843] mb-8 animate-pulse-gold">
        +{xpEarned} XP
      </div>

      <div className="flex justify-center gap-3">
        <button
          onClick={onContinue}
          className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-br from-[#8a6d2b] to-[#d4a843] text-[#0a0a12] rounded-lg font-heading text-[0.9rem] tracking-[1px] shadow-[0_4px_15px_rgba(212,168,67,0.3)] hover:-translate-y-0.5 hover:shadow-[0_6px_25px_rgba(212,168,67,0.4)] active:translate-y-0 transition-all cursor-pointer"
        >
          Continue Quest {'\u2192'}
        </button>
        <button
          onClick={onReplay}
          className="inline-flex items-center gap-2 px-5 py-2 border border-[#8a6d2b] text-[#f0d078] rounded-lg font-heading text-[0.8rem] tracking-[1px] bg-transparent hover:bg-[rgba(212,168,67,0.1)] hover:border-[#d4a843] transition-all cursor-pointer"
        >
          Replay Chapter
        </button>
      </div>
    </div>
  );
}
