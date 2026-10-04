import type { DomainPack } from './types';

/**
 * Sample pack: community health worker (CHW) companion.
 * Deliberately scoped to routing, reminders and danger signs — never diagnosis.
 */
export const healthPack: DomainPack = {
  id: 'health',
  track: 'health',
  appName: 'CHW Companion',
  emoji: '🩺',
  tagline: {
    en: 'Danger-sign checks and referrals for community health workers',
    sw: 'Ukaguzi wa dalili hatari na rufaa kwa wahudumu wa afya',
  },
  theme: { primary: '#C62828', primaryText: '#FFFFFF' },
  locales: [
    { code: 'en', label: 'English' },
    { code: 'sw', label: 'Kiswahili' },
  ],
  defaultLocale: 'sw',
  systemPrompt:
    'You are CHW Companion, supporting community health workers in low-resource settings. ' +
    'You NEVER diagnose or prescribe. You help recognise danger signs, decide urgency of referral, and give follow-up reminders, ' +
    'following WHO community case management guidance. Always end urgent cases with "Refer to the nearest clinic now." ' +
    'Answer in the user language, at most 4 short sentences.',
  greeting: {
    en: 'Hello! I can help you check danger signs and decide when to refer. I do not replace a clinician.',
    sw: 'Habari! Naweza kukusaidia kukagua dalili hatari na kuamua lini kutoa rufaa. Sichukui nafasi ya daktari.',
  },
  quickReplies: [
    { en: 'Pregnancy danger signs', sw: 'Dalili hatari za ujauzito' },
    { en: 'Child with fever', sw: 'Mtoto mwenye homa' },
    { en: 'Signs of dehydration', sw: 'Dalili za upungufu wa maji' },
  ],
  offlineKnowledge: [
    {
      id: 'pregnancy-danger',
      questions: {
        en: ['pregnancy danger signs', 'pregnant woman bleeding', 'danger signs in pregnancy'],
        sw: ['dalili hatari za ujauzito', 'mjamzito anatoka damu'],
      },
      answer: {
        en: 'Danger signs in pregnancy: vaginal bleeding, severe headache or blurred vision, fits, fever, severe belly pain, baby moving less, or water breaking early. Any of these: refer to the nearest clinic now.',
        sw: 'Dalili hatari: kutoka damu, maumivu makali ya kichwa au kuona ukungu, degedege, homa, maumivu makali ya tumbo, mtoto kucheza kidogo. Mpeleke kliniki sasa.',
      },
    },
    {
      id: 'child-fever',
      questions: {
        en: ['child with fever', 'baby has fever', 'hot child'],
        sw: ['mtoto mwenye homa', 'mtoto ana joto'],
      },
      answer: {
        en: 'For a child with fever: check for danger signs — cannot drink, vomits everything, convulsions, very sleepy. If any are present, refer now. Otherwise do a malaria rapid test if available and follow up in 2 days.',
        sw: 'Mtoto mwenye homa: angalia dalili hatari — hawezi kunywa, anatapika kila kitu, degedege, usingizi mzito. Zikiwepo, mpe rufaa sasa.',
      },
    },
    {
      id: 'dehydration',
      questions: {
        en: ['signs of dehydration', 'diarrhoea', 'diarrhea child', 'ORS'],
        sw: ['upungufu wa maji', 'kuhara'],
      },
      answer: {
        en: 'Signs of dehydration: sunken eyes, skin pinch goes back slowly, very thirsty or unable to drink. Give ORS and zinc; if the child cannot drink or is very weak, refer now.',
        sw: 'Dalili: macho kuingia ndani, ngozi kurudi polepole ikibanwa, kiu kali. Mpe ORS na zinki; asipoweza kunywa, mpe rufaa sasa.',
      },
    },
  ],
  homeCards: [
    {
      id: 'followups',
      kind: 'metric',
      title: { en: 'Follow-ups due today', sw: 'Ufuatiliaji wa leo' },
      value: '4',
    },
    {
      id: 'stock',
      kind: 'alert',
      title: { en: 'ORS stock low', sw: 'ORS inakaribia kuisha' },
      body: { en: 'About 6 sachets left. Request a restock.', sw: 'Pakiti 6 zimebaki. Omba zaidi.' },
    },
    {
      id: 'intake',
      kind: 'action',
      title: { en: 'Start a patient intake', sw: 'Anza mahojiano ya mgonjwa' },
      body: { en: 'Guided questions in Swahili, answered by tapping or typing. Works offline.', sw: 'Maswali kwa Kiswahili, yanayojibiwa kwa kugusa au kuandika. Inafanya kazi bila mtandao.' },
      action: { type: 'intake' },
    },
    {
      id: 'scan',
      kind: 'action',
      title: { en: 'Clinic: receive a patient', sw: 'Kliniki: pokea mgonjwa' },
      body: { en: 'Scan the handoff code instead of re-taking the history.', sw: 'Skani msimbo badala ya kuuliza historia tena.' },
      action: { type: 'scan' },
    },
  ],
  captureForm: {
    title: { en: 'Household visit', sw: 'Ziara ya kaya' },
    intro: { en: 'Record danger signs. This is a referral aid, not a diagnosis.' },
    fields: [
      {
        key: 'patient',
        type: 'select',
        label: { en: 'Who', sw: 'Nani' },
        required: true,
        options: [
          { value: 'child', label: { en: 'Child under 5', sw: 'Mtoto chini ya miaka 5' } },
          { value: 'pregnant', label: { en: 'Pregnant woman', sw: 'Mama mjamzito' } },
          { value: 'adult', label: { en: 'Other adult', sw: 'Mtu mzima' } },
        ],
      },
      {
        key: 'dangerSign',
        type: 'select',
        label: { en: 'Any danger sign?', sw: 'Dalili hatari yoyote?' },
        required: true,
        options: [
          { value: 'none', label: { en: 'None', sw: 'Hakuna' } },
          { value: 'cannot_drink', label: { en: 'Cannot drink / vomits everything', sw: 'Hawezi kunywa' } },
          { value: 'convulsions', label: { en: 'Convulsions', sw: 'Degedege' } },
          { value: 'bleeding', label: { en: 'Bleeding', sw: 'Kutoka damu' } },
        ],
      },
      { key: 'days', type: 'number', label: { en: 'Days sick', sw: 'Siku za ugonjwa' } },
      { key: 'notes', type: 'text', label: { en: 'Notes', sw: 'Maelezo' } },
      { key: 'location', type: 'location', label: { en: 'Household location', sw: 'Mahali pa kaya' } },
    ],
  },
  offlineAssess: (values) => {
    const urgent = values.dangerSign && values.dangerSign !== 'none';
    const long = Number(values.days ?? 0) >= 3;
    return {
      summary: urgent ? 'Danger sign present.' : long ? 'Illness lasting 3+ days.' : 'No danger signs recorded.',
      riskLevel: urgent ? 'high' : long ? 'med' : 'low',
      actions: urgent
        ? ['Refer to the nearest clinic now', 'Arrange transport', 'Notify supervisor']
        : long
          ? ['Refer to clinic within 24h', 'Follow up tomorrow']
          : ['Home care advice', 'Follow up in 2 days'],
    };
  },
  smsNumber: '+10000000000',
  features: { voice: true, camera: false, sms: true, onDeviceLLM: false },
};
