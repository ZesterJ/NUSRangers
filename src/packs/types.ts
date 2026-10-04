/**
 * A DomainPack holds everything problem-specific. At hackathon kickoff we write
 * one new pack (or edit a sample) instead of touching screens or AI plumbing.
 */

/** Text in several languages. `en` is required and is the fallback. */
export type Localized = { en: string } & Partial<Record<string, string>>;

export type LocaleOption = { code: string; label: string };

export type KnowledgeItem = {
  id: string;
  /** Ways a user might ask this, per locale. Used by the on-device fuzzy matcher. */
  questions: { en: string[] } & Partial<Record<string, string[]>>;
  answer: Localized;
  tags?: string[];
};

export type HomeCardAction =
  | { type: 'chat'; prompt: Localized }
  | { type: 'capture' }
  | { type: 'intake' }
  | { type: 'scan' }
  /** Clinic tab, opening the scanner or the triage reports straight away. */
  | { type: 'scanCode' }
  | { type: 'reports' }
  | { type: 'records' }
  | { type: 'url'; url: string };

export type HomeCard = {
  id: string;
  kind: 'tip' | 'alert' | 'metric' | 'action';
  /** Emoji shown before the title; defaults to the icon for `kind`. */
  icon?: string;
  /** Who sees the card on Home; omitted = everyone. */
  roles?: ('patient' | 'clinic')[];
  title: Localized;
  body?: Localized;
  /** For `metric` cards, e.g. "KES 42/kg". */
  value?: string;
  action?: HomeCardAction;
};

export type FormField =
  | { key: string; type: 'text' | 'number'; label: Localized; placeholder?: Localized; required?: boolean }
  | { key: string; type: 'select'; label: Localized; options: { value: string; label: Localized }[]; required?: boolean }
  | { key: string; type: 'photo' | 'location'; label: Localized; required?: boolean };

export type FormValues = Record<string, string | number | { lat: number; lng: number } | undefined>;

export type RiskLevel = 'low' | 'med' | 'high';

export type Assessment = {
  summary: string;
  riskLevel?: RiskLevel;
  actions: string[];
};

export type CaptureForm = {
  title: Localized;
  intro?: Localized;
  submitLabel?: Localized;
  fields: FormField[];
};

export type FeatureFlags = {
  voice: boolean;
  camera: boolean;
  sms: boolean;
  onDeviceLLM: boolean;
};

export type DomainPack = {
  id: string;
  track: 'agriculture' | 'health' | 'tourism' | 'other';
  appName: string;
  emoji: string;
  tagline: Localized;
  theme: { primary: string; primaryText: string };
  locales: LocaleOption[];
  defaultLocale: string;
  /** Persona and safety rules for the cloud LLM. Sent to the backend with every /chat call. */
  systemPrompt: string;
  greeting: Localized;
  quickReplies: Localized[];
  offlineKnowledge: KnowledgeItem[];
  homeCards: HomeCard[];
  captureForm: CaptureForm;
  /**
   * Rule-based on-device assessment used when the backend is unreachable.
   * Keep it tiny and explainable — this is part of the "Small AI" story.
   */
  offlineAssess?: (values: FormValues, locale: string) => Assessment;
  /** Number the SMS fallback composes to (backend SMS gateway). */
  smsNumber?: string;
  features: FeatureFlags;
};

export function tr(text: Localized | undefined, locale: string): string {
  if (!text) return '';
  return text[locale] ?? text.en;
}
