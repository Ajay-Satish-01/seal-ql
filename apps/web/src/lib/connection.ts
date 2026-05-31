'use client';

const STORAGE_VERSION = 'v1';
const STORAGE_PREFIX = `seal-dashboard:${STORAGE_VERSION}:connection`;
const STORAGE_URL = `${STORAGE_PREFIX}:url`;
const STORAGE_KEY = `${STORAGE_PREFIX}:api_key`;
const STORAGE_DATABASE = `${STORAGE_PREFIX}:database_id`;

export const DEFAULT_DATABASE_ID = 'default';
const LEGACY_URL_KEYS = ['seal_api_url:v1', 'seal_api_url'] as const;
const LEGACY_KEY_KEYS = ['seal_api_key:v1', 'seal_api_key'] as const;

export const DEFAULT_API_URL =
  (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_DEFAULT_API_URL) ||
  'http://localhost:8000';

let legacyMigrated = false;

function migrateLegacyStorage(): void {
  if (typeof window === 'undefined' || legacyMigrated) return;
  legacyMigrated = true;
  if (!localStorage.getItem(STORAGE_URL)) {
    for (const legacy of LEGACY_URL_KEYS) {
      const value = localStorage.getItem(legacy);
      if (value) {
        localStorage.setItem(STORAGE_URL, value);
        localStorage.removeItem(legacy);
        break;
      }
    }
  }
  if (!localStorage.getItem(STORAGE_KEY)) {
    for (const legacy of LEGACY_KEY_KEYS) {
      const value = localStorage.getItem(legacy);
      if (value) {
        localStorage.setItem(STORAGE_KEY, value);
        localStorage.removeItem(legacy);
        break;
      }
    }
  }
}

export function getStoredApiUrl(): string {
  if (typeof window === 'undefined') return DEFAULT_API_URL;
  migrateLegacyStorage();
  return localStorage.getItem(STORAGE_URL) || DEFAULT_API_URL;
}

export function getStoredApiKey(): string {
  if (typeof window === 'undefined') return '';
  migrateLegacyStorage();
  return localStorage.getItem(STORAGE_KEY) || '';
}

export function getStoredDatabaseId(): string {
  if (typeof window === 'undefined') return DEFAULT_DATABASE_ID;
  migrateLegacyStorage();
  return localStorage.getItem(STORAGE_DATABASE) || DEFAULT_DATABASE_ID;
}

export function saveConnection(apiUrl: string, apiKey: string): void {
  migrateLegacyStorage();
  localStorage.setItem(STORAGE_URL, apiUrl.trim().replace(/\/+$/, ''));
  localStorage.setItem(STORAGE_KEY, apiKey.trim());
}

export function saveDatabaseId(databaseId: string): void {
  migrateLegacyStorage();
  const trimmed = databaseId.trim();
  localStorage.setItem(
    STORAGE_DATABASE,
    trimmed.length > 0 ? trimmed : DEFAULT_DATABASE_ID,
  );
}

export function authHeaders(apiKey: string): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (apiKey) headers['X-API-Key'] = apiKey;
  return headers;
}

export function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, '');
}
