import type { DomainPack } from './types';

/** Sample pack: smallholder farming advisor ("Virtual Agronomist lite"). */
export const agriPack: DomainPack = {
  id: 'agri',
  track: 'agriculture',
  appName: 'ShambaMate',
  emoji: '🌱',
  tagline: {
    en: 'Farm advice that works without internet',
    sw: 'Ushauri wa kilimo bila intaneti',
  },
  theme: { primary: '#2E7D32', primaryText: '#FFFFFF' },
  locales: [
    { code: 'en', label: 'English' },
    { code: 'sw', label: 'Kiswahili' },
  ],
  defaultLocale: 'en',
  systemPrompt:
    'You are ShambaMate, a practical agronomy assistant for smallholder farmers in East Africa. ' +
    'Answer in the user language, in at most 4 short sentences, using simple words. ' +
    'Prefer low-cost, locally available inputs. If unsure, say so and suggest contacting the local extension officer.',
  greeting: {
    en: 'Hello! Ask me about planting, pests, fertilizer or where to sell your harvest.',
    sw: 'Habari! Niulize kuhusu kupanda, wadudu, mbolea au wapi pa kuuza mavuno.',
  },
  quickReplies: [
    { en: 'When should I plant maize?', sw: 'Nipande mahindi lini?' },
    { en: 'Leaves have holes, what pest?', sw: 'Majani yana mashimo, ni mdudu gani?' },
    { en: 'Where can I sell for a better price?', sw: 'Niuze wapi kwa bei nzuri?' },
  ],
  offlineKnowledge: [
    {
      id: 'maize-planting',
      questions: {
        en: ['when to plant maize', 'maize planting time', 'best time to plant corn'],
        sw: ['nipande mahindi lini', 'wakati wa kupanda mahindi'],
      },
      answer: {
        en: 'Plant maize at the start of the long rains, once the soil is moist to about 15 cm. Space rows 75 cm apart and plants 25 cm apart.',
        sw: 'Panda mahindi mwanzoni mwa mvua za masika, udongo ukiwa na unyevu hadi sentimita 15. Mistari sentimita 75, mimea sentimita 25.',
      },
      tags: ['planting'],
    },
    {
      id: 'fall-armyworm',
      questions: {
        en: ['holes in maize leaves', 'leaves have holes what pest', 'fall armyworm', 'caterpillar in maize'],
        sw: ['majani yana mashimo', 'viwavi jeshi', 'mdudu kwenye mahindi'],
      },
      answer: {
        en: 'Ragged holes and sawdust-like droppings in the maize funnel usually mean fall armyworm. Check 20 plants; if more than 5 are hit, apply ash or a recommended bio-pesticide into the funnel early morning.',
        sw: 'Mashimo na kinyesi kama unga wa mbao ndani ya mahindi ni dalili za viwavi jeshi. Kagua mimea 20; ikiwa zaidi ya 5 imeathirika, weka majivu au dawa ya kibaiolojia asubuhi.',
      },
      tags: ['pest'],
    },
    {
      id: 'fertilizer',
      questions: {
        en: ['what fertilizer should i use', 'fertilizer for maize', 'how much fertilizer', 'manure'],
        sw: ['mbolea gani', 'mbolea ya mahindi'],
      },
      answer: {
        en: 'At planting use DAP or well-rotted manure (2 handfuls per hole). Top-dress with CAN when maize is knee-high. A soil test gives the most accurate advice.',
        sw: 'Wakati wa kupanda tumia DAP au samadi iliyooza (viganja 2 kwa shimo). Ongeza CAN mahindi yakifika gotini.',
      },
      tags: ['inputs'],
    },
    {
      id: 'sell-price',
      questions: {
        en: ['where can i sell', 'better price', 'market price', 'where to sell harvest'],
        sw: ['niuze wapi', 'bei nzuri', 'bei ya soko'],
      },
      answer: {
        en: 'Compare prices at two nearby markets before selling, and subtract transport cost. Selling 1–2 months after harvest often earns more if you can store grain dry (below 13% moisture).',
        sw: 'Linganisha bei za masoko mawili ya karibu na utoe gharama ya usafiri. Kuuza miezi 1–2 baada ya mavuno mara nyingi hulipa zaidi ikiwa umehifadhi nafaka kavu.',
      },
      tags: ['market'],
    },
    {
      id: 'storage',
      questions: {
        en: ['how to store grain', 'weevils in storage', 'stop grain rotting'],
        sw: ['kuhifadhi nafaka', 'wadudu ghalani'],
      },
      answer: {
        en: 'Dry grain until it cracks when bitten, then store in hermetic (airtight) bags off the floor. This stops weevils without chemicals.',
        sw: 'Kausha nafaka hadi ivunjike ukiiuma, kisha hifadhi kwenye mifuko isiyopitisha hewa juu ya sakafu.',
      },
      tags: ['post-harvest'],
    },
  ],
  homeCards: [
    {
      id: 'weather',
      kind: 'alert',
      title: { en: 'Rain expected in 3 days', sw: 'Mvua inatarajiwa baada ya siku 3' },
      body: { en: 'Good window to prepare land and plant.', sw: 'Wakati mzuri wa kuandaa shamba na kupanda.' },
    },
    {
      id: 'price',
      kind: 'metric',
      title: { en: 'Maize price, nearest market', sw: 'Bei ya mahindi, soko la karibu' },
      value: 'KES 42 / kg',
      body: { en: '↑ 8% vs last month', sw: '↑ 8% ukilinganisha na mwezi uliopita' },
    },
    {
      id: 'ask-pest',
      kind: 'action',
      title: { en: 'Something wrong with your crop?', sw: 'Zao lako lina tatizo?' },
      body: { en: 'Report it with a photo and get advice.', sw: 'Ripoti kwa picha upate ushauri.' },
      action: { type: 'capture' },
    },
    {
      id: 'tip',
      kind: 'tip',
      title: { en: 'Tip of the week', sw: 'Dokezo la wiki' },
      body: { en: 'Scout 20 plants in a W pattern to check for pests.', sw: 'Kagua mimea 20 kwa mwendo wa W kutafuta wadudu.' },
      action: { type: 'chat', prompt: { en: 'How do I scout for pests?', sw: 'Ninakaguaje wadudu?' } },
    },
  ],
  captureForm: {
    title: { en: 'Crop problem report', sw: 'Ripoti ya tatizo la zao' },
    intro: { en: 'Tell us what you see. Works offline — we send it when you are back online.' },
    fields: [
      {
        key: 'crop',
        type: 'select',
        label: { en: 'Crop', sw: 'Zao' },
        required: true,
        options: [
          { value: 'maize', label: { en: 'Maize', sw: 'Mahindi' } },
          { value: 'beans', label: { en: 'Beans', sw: 'Maharagwe' } },
          { value: 'cassava', label: { en: 'Cassava', sw: 'Muhogo' } },
        ],
      },
      {
        key: 'symptom',
        type: 'select',
        label: { en: 'What do you see?', sw: 'Unaona nini?' },
        required: true,
        options: [
          { value: 'holes', label: { en: 'Holes in leaves', sw: 'Mashimo kwenye majani' } },
          { value: 'yellow', label: { en: 'Yellow leaves', sw: 'Majani ya njano' } },
          { value: 'wilting', label: { en: 'Wilting', sw: 'Kunyauka' } },
          { value: 'spots', label: { en: 'Spots on leaves', sw: 'Madoa kwenye majani' } },
        ],
      },
      { key: 'affected', type: 'number', label: { en: 'Plants affected out of 20', sw: 'Mimea iliyoathirika kati ya 20' } },
      { key: 'photo', type: 'photo', label: { en: 'Photo of the plant', sw: 'Picha ya mmea' } },
      { key: 'location', type: 'location', label: { en: 'Farm location', sw: 'Mahali pa shamba' } },
    ],
  },
  offlineAssess: (values) => {
    const affected = Number(values.affected ?? 0);
    const riskLevel = affected >= 10 ? 'high' : affected >= 5 ? 'med' : 'low';
    const bySymptom: Record<string, string> = {
      holes: 'Likely fall armyworm or another chewing pest.',
      yellow: 'Likely nitrogen shortage or waterlogging.',
      wilting: 'Likely drought stress or bacterial wilt.',
      spots: 'Likely a fungal leaf disease.',
    };
    return {
      summary: bySymptom[String(values.symptom)] ?? 'Unclear problem — more information needed.',
      riskLevel,
      actions:
        riskLevel === 'high'
          ? ['Treat today', 'Contact your extension officer', 'Re-check in 3 days']
          : ['Monitor 20 plants every 3 days', 'Remove badly affected leaves'],
    };
  },
  smsNumber: '+10000000000',
  features: { voice: true, camera: true, sms: true, onDeviceLLM: false },
};
