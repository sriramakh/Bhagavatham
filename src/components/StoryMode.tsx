'use client';

import React, { memo } from 'react';
import { StoryBeat } from '@/types';

interface StoryModeProps {
  story: StoryBeat[];
  chapterLabel: string;
  title: string;
  onContinue: () => void;
  onBack: () => void;
}

const StoryMode = memo(function StoryMode({
  story,
  chapterLabel,
  title,
  onContinue,
  onBack,
}: StoryModeProps) {
  return (
    <div className="max-w-[700px] mx-auto animate-fadeIn">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="font-heading text-[#8a6d2b] text-[0.75rem] tracking-[2px] uppercase">
          {chapterLabel}
        </div>
        <h2 className="font-heading text-[#f0d078] text-[1.5rem] mt-1">{title}</h2>
      </div>

      {/* Story body */}
      <div className="leading-[1.8]">
        {story.map((beat, i) => {
          if (beat.type === 'narration') {
            return (
              <div
                key={i}
                className="text-[#e8e0d0] text-[0.95rem] mb-5 animate-storyReveal"
                style={{ animationDelay: `${i * 0.15}s` }}
                dangerouslySetInnerHTML={{
                  __html: beat.text.replace(
                    /class="story-highlight"/g,
                    'class="text-[#f0d078] font-semibold"'
                  ),
                }}
              />
            );
          }

          if (beat.type === 'dialogue') {
            return (
              <div
                key={i}
                className="border-l-[3px] border-[#8a6d2b] pl-5 py-3 my-5 bg-[rgba(212,168,67,0.05)] rounded-r-lg italic animate-storyReveal"
                style={{ animationDelay: `${i * 0.15}s` }}
              >
                <span className="font-heading text-[#f4a03b] not-italic text-[0.8rem] tracking-[1px] block mb-1">
                  {beat.speaker}
                </span>
                <span
                  className="text-[#e8e0d0] text-[0.95rem]"
                  dangerouslySetInnerHTML={{
                    __html: `"${beat.text.replace(
                      /class="story-highlight"/g,
                      'class="text-[#f0d078] font-semibold"'
                    )}"`,
                  }}
                />
              </div>
            );
          }

          return null;
        })}
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center mt-10 pt-5 border-t border-[#2a2a3e]">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 px-5 py-2 border border-[#8a6d2b] text-[#f0d078] rounded-lg font-heading text-[0.8rem] tracking-[1px] bg-transparent hover:bg-[rgba(212,168,67,0.1)] hover:border-[#d4a843] transition-all cursor-pointer"
        >
          {'\u2190'} Chapters
        </button>
        <button
          onClick={onContinue}
          className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-br from-[#8a6d2b] to-[#d4a843] text-[#0a0a12] rounded-lg font-heading text-[0.9rem] tracking-[1px] shadow-[0_4px_15px_rgba(212,168,67,0.3)] hover:-translate-y-0.5 hover:shadow-[0_6px_25px_rgba(212,168,67,0.4)] active:translate-y-0 transition-all cursor-pointer"
        >
          Continue to Verse Study {'\u2192'}
        </button>
      </div>
    </div>
  );
});

export default StoryMode;
