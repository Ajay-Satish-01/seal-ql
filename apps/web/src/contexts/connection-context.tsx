'use client';

import {
  readTrustExplainabilityFromEnv,
} from '@seal/trust-explainability';
import {
  DEFAULT_API_URL,
  DEFAULT_DATABASE_ID,
  getStoredApiKey,
  getStoredApiUrl,
  getStoredDatabaseId,
  saveConnection,
  saveDatabaseId,
} from '@/lib/connection';
import type { DatabaseInfo } from '@/lib/seal-api';
import { getDatabases } from '@/lib/seal-api';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

type ConnectionContextValue = {
  apiUrl: string;
  apiKey: string;
  databaseId: string;
  registeredDatabases: DatabaseInfo[];
  revision: number;
  trustExplainabilityEnabled: boolean;
  setConnection: (apiUrl: string, apiKey: string) => void;
  setDatabaseId: (databaseId: string) => void;
  registerDatabases: (list: DatabaseInfo[]) => void;
  setTrustExplainabilityEnabled: (enabled: boolean) => void;
  refreshDatabases: () => Promise<void>;
};

const ConnectionContext = createContext<ConnectionContextValue | null>(null);

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [apiKey, setApiKey] = useState('');
  const [databaseId, setDatabaseIdState] = useState(DEFAULT_DATABASE_ID);
  const [registeredDatabases, setRegisteredDatabases] = useState<DatabaseInfo[]>([
    { database_id: DEFAULT_DATABASE_ID, dialect: 'postgres', is_default: true },
  ]);
  const [revision, setRevision] = useState(0);
  const [trustExplainabilityEnabled, setTrustExplainabilityEnabled] = useState(
    readTrustExplainabilityFromEnv,
  );

  useEffect(() => {
    // Hydrate from localStorage after mount (not available during SSR).
    /* eslint-disable react-hooks/set-state-in-effect */
    setApiUrl(getStoredApiUrl());
    setApiKey(getStoredApiKey());
    setDatabaseIdState(getStoredDatabaseId());
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  const registerDatabases = useCallback(
    (list: DatabaseInfo[]) => {
      const normalized =
        list.length > 0
          ? list
          : [{ database_id: DEFAULT_DATABASE_ID, dialect: 'postgres', is_default: true }];
      setRegisteredDatabases(normalized);
      if (!normalized.some((d) => d.database_id === databaseId)) {
        const fallback =
          normalized.find((d) => d.is_default)?.database_id ?? normalized[0].database_id;
        saveDatabaseId(fallback);
        setDatabaseIdState(fallback);
        setRevision((n) => n + 1);
      }
    },
    [databaseId],
  );

  const refreshDatabases = useCallback(async () => {
    try {
      const list = await getDatabases(apiUrl, apiKey);
      registerDatabases(list);
    } catch {
      registerDatabases([]);
    }
  }, [apiUrl, apiKey, registerDatabases]);

  const setConnection = useCallback((url: string, key: string) => {
    const trimmedUrl = url.trim().replace(/\/+$/, '');
    const trimmedKey = key.trim();
    saveConnection(trimmedUrl, trimmedKey);
    setApiUrl(trimmedUrl);
    setApiKey(trimmedKey);
    setRevision((n) => n + 1);
  }, []);

  const setDatabaseId = useCallback((id: string) => {
    const trimmed = id.trim() || DEFAULT_DATABASE_ID;
    saveDatabaseId(trimmed);
    setDatabaseIdState(trimmed);
    setRevision((n) => n + 1);
  }, []);

  const value = useMemo(
    () => ({
      apiUrl,
      apiKey,
      databaseId,
      registeredDatabases,
      revision,
      trustExplainabilityEnabled,
      setConnection,
      setDatabaseId,
      registerDatabases,
      setTrustExplainabilityEnabled,
      refreshDatabases,
    }),
    [
      apiUrl,
      apiKey,
      databaseId,
      registeredDatabases,
      revision,
      trustExplainabilityEnabled,
      setConnection,
      setDatabaseId,
      registerDatabases,
      refreshDatabases,
    ],
  );

  return <ConnectionContext.Provider value={value}>{children}</ConnectionContext.Provider>;
}

export function useConnection(): ConnectionContextValue {
  const ctx = useContext(ConnectionContext);
  if (!ctx) {
    throw new Error('useConnection must be used within ConnectionProvider');
  }
  return ctx;
}
