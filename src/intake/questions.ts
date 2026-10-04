import type { Localized } from '@/packs/types';

/**
 * Fixed guided questions (no free-form chat): each answer is short and on one topic,
 * which keeps extraction reliable.
 * `samples` are suggested answers the user can tap instead of speaking or typing.
 * Swahili text needs review by a native speaker.
 */
export type GuidedQuestion = {
  id: 'who' | 'complaint' | 'duration' | 'danger';
  prompt: Localized;
  hint: Localized;
  samples: { sw: string; en: string }[];
};

export const QUESTIONS: GuidedQuestion[] = [
  {
    id: 'who',
    prompt: { en: 'Who is the patient?', sw: 'Nani anaumwa?' },
    hint: { en: 'For example: my child, me (pregnant), my husband', sw: 'Mfano: mtoto wangu, mimi (mjamzito), mume wangu' },
    samples: [
      { sw: 'Mtoto wangu wa miaka miwili', en: 'My two-year-old child' },
      { sw: 'Mimi, nina mimba ya miezi saba', en: 'Me, I am seven months pregnant' },
    ],
  },
  {
    id: 'complaint',
    prompt: { en: 'What is wrong?', sw: 'Tatizo ni nini?' },
    hint: { en: 'Say what hurts or feels wrong', sw: 'Eleza unachohisi au kuona' },
    samples: [
      { sw: 'Ana homa kali na anakohoa', en: 'He has a high fever and is coughing' },
      { sw: 'Ninaumwa sana kichwa na naona ukungu', en: 'I have a bad headache and blurred vision' },
    ],
  },
  {
    id: 'duration',
    prompt: { en: 'How many days has this lasted?', sw: 'Imekuwa hivi kwa muda gani?' },
    hint: { en: 'For example: since yesterday, three days', sw: 'Mfano: tangu jana, siku tatu' },
    samples: [
      { sw: 'Siku tatu', en: 'Three days' },
      { sw: 'Tangu jana', en: 'Since yesterday' },
    ],
  },
  {
    id: 'danger',
    prompt: {
      en: 'Does the patient have any of these danger signs?',
      sw: 'Je, kuna yoyote kati ya haya: hawezi kunywa, anatapika kila kitu, degedege, usingizi mzito, kutoka damu?',
    },
    hint: { en: 'Tap all that apply, or tap "None of these"', sw: 'Taja ipi, au sema "hakuna"' },
    samples: [
      { sw: 'Hawezi kunywa na anatapika kila kitu', en: 'Cannot drink and vomits everything' },
      { sw: 'Hakuna', en: 'None' },
    ],
  },
];
