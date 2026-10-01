import type { DomainPack } from './types';

/** Sample pack: assistant for micro tourism businesses (homestays, guides). */
export const tourismPack: DomainPack = {
  id: 'tourism',
  track: 'tourism',
  appName: 'HostMate',
  emoji: '🏡',
  tagline: {
    en: 'Pricing, bookings and guest replies for small hosts',
    es: 'Precios, reservas y respuestas a huéspedes para pequeños anfitriones',
  },
  theme: { primary: '#00838F', primaryText: '#FFFFFF' },
  locales: [
    { code: 'en', label: 'English' },
    { code: 'es', label: 'Español' },
  ],
  defaultLocale: 'en',
  systemPrompt:
    'You are HostMate, a business assistant for rural homestay owners and local guides. ' +
    'Help with pricing, demand, guest communication (you may draft replies in the guest language), and simple marketing. ' +
    'Be concrete, use local currency, and keep answers under 4 short sentences.',
  greeting: {
    en: 'Hi! Ask me what to charge, how busy next month will be, or to draft a reply to a guest.',
    es: '¡Hola! Pregúntame cuánto cobrar, cuánta demanda habrá o pídeme redactar una respuesta a un huésped.',
  },
  quickReplies: [
    { en: 'What price should I charge this weekend?', es: '¿Qué precio cobro este fin de semana?' },
    { en: 'Draft a reply to a guest in English', es: 'Redacta una respuesta a un huésped en inglés' },
    { en: 'How do I get more bookings?', es: '¿Cómo consigo más reservas?' },
  ],
  offlineKnowledge: [
    {
      id: 'pricing',
      questions: {
        en: ['what price should i charge', 'how much to charge', 'room price', 'weekend price'],
        es: ['qué precio cobro', 'cuánto cobrar', 'precio de la habitación'],
      },
      answer: {
        en: 'Start from your normal price and add 15–25% on weekends and local festivals, and 10% less on quiet weekdays. Check 3 similar places nearby so you stay within their range.',
        es: 'Parte de tu precio normal y súbelo 15–25% en fines de semana y fiestas locales; baja 10% entre semana. Compara con 3 lugares similares cerca.',
      },
    },
    {
      id: 'more-bookings',
      questions: {
        en: ['more bookings', 'get more guests', 'marketing', 'how to get customers'],
        es: ['más reservas', 'conseguir huéspedes', 'publicidad'],
      },
      answer: {
        en: 'Take 5 bright daytime photos, list on at least one free platform, reply to messages within an hour, and ask every happy guest for a review.',
        es: 'Toma 5 fotos luminosas de día, publica en al menos una plataforma gratuita, responde en menos de una hora y pide reseñas a los huéspedes contentos.',
      },
    },
    {
      id: 'reply-guest',
      questions: {
        en: ['draft a reply to a guest', 'reply to guest', 'answer guest message'],
        es: ['responder a un huésped', 'redacta una respuesta'],
      },
      answer: {
        en: 'Template: "Hello [name], thank you for your message! The room is available on [dates] for [price] per night, breakfast included. Shall I reserve it for you?"',
        es: 'Plantilla: "Hola [nombre], ¡gracias por tu mensaje! La habitación está disponible [fechas] por [precio] la noche, desayuno incluido. ¿La reservo?"',
      },
    },
  ],
  homeCards: [
    {
      id: 'demand',
      kind: 'metric',
      title: { en: 'Expected demand next 30 days', es: 'Demanda esperada próximos 30 días' },
      value: '↑ High',
      body: { en: 'Local festival on the 14th', es: 'Fiesta local el día 14' },
    },
    {
      id: 'price-suggestion',
      kind: 'tip',
      title: { en: 'Suggested price this weekend', es: 'Precio sugerido este fin de semana' },
      body: { en: 'Raise to 45 per night (+20%)', es: 'Sube a 45 por noche (+20%)' },
      action: { type: 'chat', prompt: { en: 'Why should I raise my price?', es: '¿Por qué debo subir el precio?' } },
    },
    {
      id: 'log',
      kind: 'action',
      title: { en: 'Log a booking or enquiry', es: 'Registrar reserva o consulta' },
      action: { type: 'capture' },
    },
  ],
  captureForm: {
    title: { en: 'Booking / enquiry', es: 'Reserva / consulta' },
    fields: [
      {
        key: 'kind',
        type: 'select',
        label: { en: 'Type', es: 'Tipo' },
        required: true,
        options: [
          { value: 'booking', label: { en: 'Booking', es: 'Reserva' } },
          { value: 'enquiry', label: { en: 'Enquiry only', es: 'Solo consulta' } },
        ],
      },
      { key: 'nights', type: 'number', label: { en: 'Nights', es: 'Noches' } },
      { key: 'price', type: 'number', label: { en: 'Price per night', es: 'Precio por noche' } },
      { key: 'guestCountry', type: 'text', label: { en: 'Guest country', es: 'País del huésped' } },
    ],
  },
  offlineAssess: (values) => {
    const nights = Number(values.nights ?? 0);
    const price = Number(values.price ?? 0);
    const revenue = nights * price;
    return {
      summary: values.kind === 'booking' ? `Booking logged: ${nights} nights, revenue ${revenue}.` : 'Enquiry logged.',
      riskLevel: 'low',
      actions: values.kind === 'booking' ? ['Send confirmation', 'Ask for review after stay'] : ['Reply within 1 hour'],
    };
  },
  smsNumber: '+10000000000',
  features: { voice: true, camera: true, sms: true, onDeviceLLM: false },
};
