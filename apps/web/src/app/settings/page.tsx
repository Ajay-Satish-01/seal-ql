'use client';

import { PageShell } from '@/components/dashboard/page-shell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useConnection } from '@/hooks/use-connection';
import {
  applyWorkspaceSettings,
  getWorkspaceSettings,
  patchWorkspaceSettings,
  type WorkspaceSettingsResponse,
} from '@/lib/seal-api';
import { notifyErrorFrom, notifyInfo, notifySuccess } from '@/lib/toast';
import { useEffect, useRef, useState, useTransition } from 'react';

type FieldMeta = {
  key: string;
  env_name: string;
  hot_reload: boolean;
  value_type: string;
  description: string;
  default: unknown;
};

export default function SettingsPage() {
  const { apiUrl, apiKey } = useConnection();
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [schema, setSchema] = useState<FieldMeta[]>([]);
  const [restartRequired, setRestartRequired] = useState<string[]>([]);
  const [storage, setStorage] = useState<WorkspaceSettingsResponse['storage']>(undefined);
  const [pendingApply, setPendingApply] = useState<string[]>([]);
  const [isPending, startTransition] = useTransition();
  const [isSaving, startSaveTransition] = useTransition();
  const [isApplying, startApplyTransition] = useTransition();
  // Snapshot of last-loaded values so Save only sends fields the user changed.
  const baselineRef = useRef<Record<string, unknown>>({});

  function syncFromResponse(res: WorkspaceSettingsResponse) {
    setSettings(res.settings);
    baselineRef.current = res.settings;
    setPendingApply(res.pending_apply ?? []);
    setRestartRequired(res.restart_required ?? []);
    setStorage(res.storage);
  }

  function load(options?: { silent?: boolean }) {
    startTransition(async () => {
      try {
        const res = await getWorkspaceSettings(apiUrl, apiKey);
        setSchema(res.schema ?? []);
        syncFromResponse(res);
        if (!options?.silent) {
          notifySuccess('Settings loaded');
        }
      } catch (e) {
        notifyErrorFrom(e, 'Failed to load settings');
      }
    });
  }

  useEffect(() => {
    load({ silent: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiUrl, apiKey]);

  function setValue(key: string, raw: string) {
    const field = schema.find((f) => f.key === key);
    let value: unknown = raw;
    if (field?.value_type === 'bool') {
      value = raw === 'true';
    } else if (field?.value_type === 'int') {
      const parsed = parseInt(raw, 10);
      // Keep an empty string while the field is being edited; it is skipped on
      // save rather than sent as NaN/null (which the API would reject).
      value = Number.isNaN(parsed) ? '' : parsed;
    }
    setSettings((prev) => ({ ...prev, [key]: value }));
  }

  function changedSettings(): Record<string, unknown> {
    const changed: Record<string, unknown> = {};
    for (const field of schema) {
      const value = settings[field.key];
      if (value === baselineRef.current[field.key]) continue;
      if (field.value_type === 'int' && (typeof value !== 'number' || Number.isNaN(value))) {
        continue;
      }
      changed[field.key] = value;
    }
    return changed;
  }

  function save() {
    const patch = changedSettings();
    if (Object.keys(patch).length === 0) {
      notifyInfo('No changes to save');
      return;
    }
    startSaveTransition(async () => {
      try {
        const res = await patchWorkspaceSettings(apiUrl, apiKey, patch);
        syncFromResponse(res);
        if ((res.hot_reload_applied?.length ?? 0) > 0) {
          notifySuccess(`Applied to running API: ${res.hot_reload_applied!.join(', ')}`);
        } else if ((res.pending_apply?.length ?? 0) > 0) {
          notifySuccess(
            'Saved to database. Click Apply to API to load changes into the running process.',
          );
        } else {
          notifySuccess('Settings saved');
        }
      } catch (e) {
        notifyErrorFrom(e, 'Save failed');
      }
    });
  }

  function applyToApi() {
    startApplyTransition(async () => {
      try {
        const res = await applyWorkspaceSettings(apiUrl, apiKey);
        syncFromResponse(res);
        if ((res.hot_reload_applied?.length ?? 0) > 0) {
          notifySuccess(`Applied to running API: ${res.hot_reload_applied!.join(', ')}`);
        } else {
          notifyInfo('Nothing pending to apply');
        }
      } catch (e) {
        notifyErrorFrom(e, 'Apply failed');
      }
    });
  }

  return (
    <PageShell
      title="Workspace settings"
      description="Saves to Postgres (primary). Missing keys fall back to workspace.json, then .env. Dev applies hot-reload on save; prod uses Apply to API."
    >
      {storage && (
        <Card className="console-panel text-muted-foreground p-4 font-mono text-xs">
          Storage: read settings from {storage.settings_read_source ?? 'env'}, catalog from{' '}
          {storage.catalog_read_source ?? 'env'}, writes → {storage.write_target ?? 'postgres'}
        </Card>
      )}
      {restartRequired.length > 0 && (
        <Card className="border-amber-500/40 bg-amber-500/10 p-4 text-sm">
          Restart the API container to apply: {restartRequired.join(', ')}
        </Card>
      )}

      <div className="space-y-4">
        {schema.map((field) => (
          <Card key={field.key} className="console-panel space-y-2 p-4">
            <div className="flex items-center justify-between gap-2">
              <code className="text-sm">{field.key}</code>
              <span className="text-muted-foreground text-xs">
                {field.hot_reload ? 'hot reload' : 'restart'}
              </span>
            </div>
            <p className="text-muted-foreground text-xs">{field.description}</p>
            {field.value_type === 'bool' ? (
              <select
                value={String(settings[field.key] ?? field.default)}
                onChange={(e) => setValue(field.key, e.target.value)}
                className="border-input bg-background w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="true">true</option>
                <option value="false">false</option>
              </select>
            ) : (
              <input
                type={field.value_type === 'int' ? 'number' : 'text'}
                value={String(settings[field.key] ?? field.default ?? '')}
                onChange={(e) => setValue(field.key, e.target.value)}
                className="border-input bg-background w-full rounded-md border px-3 py-2 font-mono text-sm"
              />
            )}
          </Card>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button onClick={save} disabled={isSaving || isPending || schema.length === 0}>
          {isSaving ? 'Saving…' : 'Save settings'}
        </Button>
        <Button
          variant="secondary"
          onClick={applyToApi}
          disabled={isApplying || isPending || pendingApply.length === 0}
        >
          {isApplying ? 'Applying…' : 'Apply to API'}
        </Button>
      </div>
    </PageShell>
  );
}
