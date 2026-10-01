import * as SQLite from 'expo-sqlite';

import type { AiSource } from '@/ai/types';
import type { Assessment, FormValues } from '@/packs/types';

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

export function getDb() {
  if (!dbPromise) {
    dbPromise = (async () => {
      const db = await SQLite.openDatabaseAsync('nusrangers.db');
      await db.execAsync(`
        PRAGMA journal_mode = WAL;
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          pack_id TEXT NOT NULL,
          role TEXT NOT NULL,
          text TEXT NOT NULL,
          source TEXT,
          suggest_sms INTEGER DEFAULT 0,
          created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reports (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          pack_id TEXT NOT NULL,
          fields TEXT NOT NULL,
          image_base64 TEXT,
          result TEXT,
          result_source TEXT,
          created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS answer_cache (
          pack_id TEXT NOT NULL,
          locale TEXT NOT NULL,
          question TEXT NOT NULL,
          answer TEXT NOT NULL,
          PRIMARY KEY (pack_id, locale, question)
        );
        CREATE TABLE IF NOT EXISTS outbox (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          kind TEXT NOT NULL,
          ref_id INTEGER NOT NULL,
          payload TEXT NOT NULL,
          created_at INTEGER NOT NULL
        );
      `);
      return db;
    })();
  }
  return dbPromise;
}

// ---------- messages ----------

export type StoredMessage = {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  source: AiSource | null;
  suggestSms: boolean;
  createdAt: number;
};

type MessageRow = {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  source: AiSource | null;
  suggest_sms: number;
  created_at: number;
};

export async function listMessages(packId: string): Promise<StoredMessage[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<MessageRow>(
    'SELECT * FROM messages WHERE pack_id = ? ORDER BY id ASC',
    packId,
  );
  return rows.map((r) => ({
    id: r.id,
    role: r.role,
    text: r.text,
    source: r.source,
    suggestSms: !!r.suggest_sms,
    createdAt: r.created_at,
  }));
}

export async function addMessage(
  packId: string,
  m: { role: 'user' | 'assistant'; text: string; source?: AiSource; suggestSms?: boolean },
) {
  const db = await getDb();
  const res = await db.runAsync(
    'INSERT INTO messages (pack_id, role, text, source, suggest_sms, created_at) VALUES (?, ?, ?, ?, ?, ?)',
    packId,
    m.role,
    m.text,
    m.source ?? null,
    m.suggestSms ? 1 : 0,
    Date.now(),
  );
  return res.lastInsertRowId;
}

export async function clearMessages(packId: string) {
  const db = await getDb();
  await db.runAsync('DELETE FROM messages WHERE pack_id = ?', packId);
}

// ---------- answer cache (cloud answers reused offline) ----------

export const normalizeQuestion = (q: string) =>
  q.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, '').replace(/\s+/g, ' ').trim();

export async function cacheAnswer(packId: string, locale: string, question: string, answer: string) {
  const db = await getDb();
  await db.runAsync(
    'INSERT OR REPLACE INTO answer_cache (pack_id, locale, question, answer) VALUES (?, ?, ?, ?)',
    packId,
    locale,
    normalizeQuestion(question),
    answer,
  );
}

export async function getCachedAnswer(packId: string, locale: string, question: string) {
  const db = await getDb();
  const row = await db.getFirstAsync<{ answer: string }>(
    'SELECT answer FROM answer_cache WHERE pack_id = ? AND locale = ? AND question = ?',
    packId,
    locale,
    normalizeQuestion(question),
  );
  return row?.answer ?? null;
}

// ---------- reports ----------

export type StoredReport = {
  id: number;
  fields: FormValues;
  result: Assessment | null;
  resultSource: AiSource | null;
  createdAt: number;
};

type ReportRow = {
  id: number;
  fields: string;
  result: string | null;
  result_source: AiSource | null;
  created_at: number;
};

export async function addReport(packId: string, fields: FormValues, imageBase64?: string) {
  const db = await getDb();
  const res = await db.runAsync(
    'INSERT INTO reports (pack_id, fields, image_base64, created_at) VALUES (?, ?, ?, ?)',
    packId,
    JSON.stringify(fields),
    imageBase64 ?? null,
    Date.now(),
  );
  return res.lastInsertRowId;
}

export async function setReportResult(id: number, result: Assessment, source: AiSource) {
  const db = await getDb();
  await db.runAsync(
    'UPDATE reports SET result = ?, result_source = ? WHERE id = ?',
    JSON.stringify(result),
    source,
    id,
  );
}

export async function listReports(packId: string): Promise<StoredReport[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<ReportRow>(
    'SELECT id, fields, result, result_source, created_at FROM reports WHERE pack_id = ? ORDER BY id DESC',
    packId,
  );
  return rows.map((r) => ({
    id: r.id,
    fields: JSON.parse(r.fields),
    result: r.result ? JSON.parse(r.result) : null,
    resultSource: r.result_source,
    createdAt: r.created_at,
  }));
}

export async function getReportImage(id: number) {
  const db = await getDb();
  const row = await db.getFirstAsync<{ image_base64: string | null }>(
    'SELECT image_base64 FROM reports WHERE id = ?',
    id,
  );
  return row?.image_base64 ?? undefined;
}

// ---------- outbox (work to retry once back online) ----------

export type OutboxKind = 'chat' | 'report';
export type OutboxItem = { id: number; kind: OutboxKind; refId: number; payload: string };

export async function enqueue(kind: OutboxKind, refId: number, payload: unknown) {
  const db = await getDb();
  await db.runAsync(
    'INSERT INTO outbox (kind, ref_id, payload, created_at) VALUES (?, ?, ?, ?)',
    kind,
    refId,
    JSON.stringify(payload),
    Date.now(),
  );
}

export async function listOutbox(): Promise<OutboxItem[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<{ id: number; kind: OutboxKind; ref_id: number; payload: string }>(
    'SELECT id, kind, ref_id, payload FROM outbox ORDER BY id ASC',
  );
  return rows.map((r) => ({ id: r.id, kind: r.kind, refId: r.ref_id, payload: r.payload }));
}

export async function removeOutbox(id: number) {
  const db = await getDb();
  await db.runAsync('DELETE FROM outbox WHERE id = ?', id);
}
