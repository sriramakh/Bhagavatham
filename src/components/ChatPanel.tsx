'use client';

import React, { memo, useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { ChatMessage, Verse } from '@/types';

interface ChatPanelProps {
  verseContext: {
    verse?: Verse;
    madhvaTeaching?: string;
    chapterTitle?: string;
  } | null;
  isOpen: boolean;
  onToggle: () => void;
}

const ChatPanel = memo(function ChatPanel({ verseContext, isOpen, onToggle }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'system',
      content:
        "Ask any question about the current shloka, its Sanskrit words, Madhvacharya's interpretation, or Bhagavatam philosophy.",
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const contextLabel = verseContext?.verse
    ? `${verseContext.verse.ref} — ${verseContext.chapterTitle || ''}`
    : 'No verse selected yet';

  const hasContext = !!verseContext?.verse;

  const suggestions = useMemo(() => {
    if (!verseContext?.verse) {
      return [
        'What is the Srimad Bhagavatam?',
        'Tell me about Madhvacharya',
        'What is Dvaita philosophy?',
        'How should I study shlokas?',
      ];
    }
    const firstWord = verseContext.verse.words[0]?.san || 'this verse';
    return [
      'What is the deeper meaning of this verse?',
      'Explain the Sanskrit grammar here',
      'How does Madhva interpret this differently from Advaita?',
      `Tell me about ${firstWord}`,
    ];
  }, [verseContext]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMsg: ChatMessage = { role: 'user', content: text.trim() };
      const newMessages = [...messages.filter((m) => m.role !== 'system'), userMsg];
      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setIsLoading(true);

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: newMessages.map((m) => ({ role: m.role, content: m.content })),
            verseContext: verseContext?.verse
              ? {
                  ref: verseContext.verse.ref,
                  sanskrit: verseContext.verse.sanskrit,
                  transliteration: verseContext.verse.transliteration,
                  translation: verseContext.verse.translation,
                  words: verseContext.verse.words,
                  madhvaTeaching: verseContext.madhvaTeaching,
                  chapterTitle: verseContext.chapterTitle,
                }
              : null,
          }),
        });

        const data = await res.json();
        if (data.error) {
          setMessages((prev) => [
            ...prev,
            {
              role: 'system',
              content: `Error: ${data.error}`,
            },
          ]);
        } else {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: data.message },
          ]);
        }
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'system',
            content: 'Failed to reach the chat server. Please try again.',
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [messages, isLoading, verseContext]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(input);
      }
    },
    [input, sendMessage]
  );

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className={`fixed bottom-6 right-6 z-[150] w-14 h-14 rounded-full border-none bg-gradient-to-br from-[#8a6d2b] to-[#d4a843] text-[#0a0a12] text-[1.5rem] cursor-pointer shadow-[0_4px_20px_rgba(212,168,67,0.4)] transition-all flex items-center justify-center hover:scale-110 hover:shadow-[0_6px_30px_rgba(212,168,67,0.5)] ${
          hasContext ? 'animate-pulse-gold' : ''
        }`}
        title="Ask about this shloka"
      >
        {'\uD83D\uDCAC'}
      </button>

      {/* Panel */}
      {isOpen && (
        <div className="fixed bottom-[90px] right-6 z-[150] w-[420px] max-h-[520px] bg-[#12121e] border border-[#8a6d2b] rounded-xl overflow-hidden shadow-[0_8px_40px_rgba(0,0,0,0.6)] flex flex-col animate-slideIn max-[600px]:w-[calc(100vw-32px)] max-[600px]:right-4 max-[600px]:bottom-20">
          {/* Header */}
          <div className="px-[18px] py-3.5 bg-gradient-to-br from-[rgba(212,168,67,0.12)] to-[rgba(212,168,67,0.04)] border-b border-[rgba(212,168,67,0.3)] flex items-center justify-between">
            <div>
              <div className="font-heading text-[#d4a843] text-[0.85rem] tracking-[1px] flex items-center gap-2">
                {'\uD83E\uDEB7'} Ask about this Shloka
              </div>
              <div className="text-[0.65rem] text-[#6b6157] mt-0.5 max-w-[280px] overflow-hidden text-ellipsis whitespace-nowrap">
                {contextLabel}
              </div>
            </div>
            <button
              onClick={onToggle}
              className="bg-transparent border-none text-[#a89b8c] text-[1.2rem] cursor-pointer px-2 py-1 hover:text-[#f0d078] transition-colors"
            >
              {'\u2715'}
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3 min-h-[250px] max-h-[340px]">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`max-w-[88%] px-3.5 py-2.5 rounded-xl text-[0.85rem] leading-[1.6] break-words ${
                  msg.role === 'user'
                    ? 'self-end bg-gradient-to-br from-[rgba(212,168,67,0.15)] to-[rgba(212,168,67,0.08)] border border-[rgba(212,168,67,0.3)] text-[#e8e0d0] rounded-br-sm'
                    : msg.role === 'assistant'
                      ? 'self-start bg-[#1a1a2e] border border-[#2a2a3e] text-[#e8e0d0] rounded-bl-sm'
                      : 'self-center text-[0.75rem] text-[#6b6157] italic px-3 py-1.5'
                }`}
              >
                {msg.content}
              </div>
            ))}
            {isLoading && (
              <div className="self-start bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl rounded-bl-sm px-3.5 py-2.5 text-[#6b6157]">
                <span className="flex gap-1">
                  {[0, 0.2, 0.4].map((delay) => (
                    <span
                      key={delay}
                      className="inline-block w-1.5 h-1.5 rounded-full bg-[#6b6157]"
                      style={{
                        animation: `typingBounce 1.4s infinite`,
                        animationDelay: `${delay}s`,
                      }}
                    />
                  ))}
                </span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions */}
          <div className="px-3 py-2 flex flex-wrap gap-1.5 border-t border-[#2a2a3e] bg-[#0a0a12]">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => sendMessage(s)}
                className="px-2.5 py-1.5 text-[0.7rem] rounded-xl bg-[#1a1a2e] border border-[#2a2a3e] text-[#a89b8c] cursor-pointer transition-all hover:border-[#8a6d2b] hover:text-[#f0d078]"
              >
                {s}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="px-3 py-3 border-t border-[#2a2a3e] flex gap-2 bg-[#0a0a12]">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about this verse..."
              className="flex-1 px-3.5 py-2.5 bg-[#1a1a2e] border border-[#2a2a3e] rounded-lg text-[#e8e0d0] text-[0.85rem] outline-none focus:border-[#8a6d2b] placeholder:text-[#6b6157]"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={isLoading || !input.trim()}
              className="px-4 py-2.5 bg-gradient-to-br from-[#8a6d2b] to-[#d4a843] border-none rounded-lg text-[#0a0a12] text-[0.9rem] cursor-pointer transition-all font-semibold hover:-translate-y-px hover:shadow-[0_2px_10px_rgba(212,168,67,0.3)] disabled:opacity-40 disabled:cursor-not-allowed disabled:translate-y-0"
            >
              {'\u2192'}
            </button>
          </div>
        </div>
      )}
    </>
  );
});

export default ChatPanel;
