'use client';

import {
  DEFAULT_API_URL,
  getStoredApiKey,
  getStoredApiUrl,
  saveConnection,
} from '@/lib/connection';
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
  revision: number;
  setConnection: (apiUrl: string, apiKey: string) => void;
};

const ConnectionContext = createContext<ConnectionContextValue | null>(null);

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [apiKey, setApiKey] = useState('');
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    // Hydrate from localStorage after mount (not available during SSR).
    /* eslint-disable react-hooks/set-state-in-effect */
    setApiUrl(getStoredApiUrl());
    setApiKey(getStoredApiKey());
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  const setConnection = useCallback((url: string, key: string) => {
    const trimmedUrl = url.trim().replace(/\/+$/, '');
    const trimmedKey = key.trim();
    saveConnection(trimmedUrl, trimmedKey);
    setApiUrl(trimmedUrl);
    setApiKey(trimmedKey);
    setRevision((n) => n + 1);
  }, []);

  const value = useMemo(
    () => ({ apiUrl, apiKey, revision, setConnection }),
    [apiUrl, apiKey, revision, setConnection],
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
