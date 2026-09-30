import * as SMS from 'expo-sms';

import type { DomainPack } from '@/packs/types';

/**
 * Opens the SMS composer addressed to the backend's SMS gateway.
 * The gateway (Twilio / Africa's Talking webhook) answers with the same brain as /chat,
 * which is our "works on a basic phone with no data" story.
 */
export async function sendViaSms(pack: DomainPack, question: string) {
  if (!pack.smsNumber || !(await SMS.isAvailableAsync())) return false;
  const text = `${pack.id.toUpperCase()}: ${question}`.slice(0, 160);
  const { result } = await SMS.sendSMSAsync([pack.smsNumber], text);
  return result === 'sent' || result === 'unknown';
}
