/**
 * Sanity checks for domain packs. Run after editing a pack: `npm run check:packs`
 * - every quick reply (in every locale) is answerable offline
 * - every pack locale has UI strings
 * - card/knowledge ids are unique
 */
import { matchOffline, STRONG_MATCH } from '@/ai/strategies/offlineMatcher';
import en from '@/i18n/locales/en.json';
import es from '@/i18n/locales/es.json';
import sw from '@/i18n/locales/sw.json';
import { PACKS } from '@/packs';

const uiLocales: Record<string, unknown> = { en, es, sw };
let problems = 0;
const fail = (msg: string) => {
  problems++;
  console.log('✗', msg);
};

for (const pack of Object.values(PACKS)) {
  for (const l of pack.locales) if (!uiLocales[l.code]) fail(`${pack.id}: no UI strings for locale "${l.code}" (add src/i18n/locales/${l.code}.json)`);

  for (const qr of pack.quickReplies) {
    for (const [locale, question] of Object.entries(qr)) {
      const m = matchOffline(pack, question as string, locale);
      if (!m || m.score > STRONG_MATCH) fail(`${pack.id}/${locale}: quick reply not answerable offline: "${question}" (score ${m?.score.toFixed(2) ?? '-'})`);
    }
  }

  for (const [name, ids] of [
    ['homeCards', pack.homeCards.map((c) => c.id)],
    ['offlineKnowledge', pack.offlineKnowledge.map((k) => k.id)],
    ['captureForm.fields', pack.captureForm.fields.map((f) => f.key)],
  ] as const) {
    const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
    if (dupes.length) fail(`${pack.id}: duplicate ${name} ids: ${dupes.join(', ')}`);
  }
  console.log(`${pack.emoji} ${pack.id}: ${pack.offlineKnowledge.length} knowledge items, ${pack.quickReplies.length} quick replies`);
}

if (problems) {
  console.log(`\n${problems} problem(s)`);
  process.exit(1);
}
console.log('\nAll packs OK');
