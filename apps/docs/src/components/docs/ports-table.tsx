const PORTS = [
  { service: 'Seal API', port: '8000', url: 'http://localhost:8000', notes: 'Swagger at /docs when SEAL_DISABLE_DOCS=false' },
  { service: 'Docs site (this site)', port: '3000', url: 'http://localhost:3000', notes: 'cd apps/docs && pnpm dev' },
  { service: 'Operational dashboard', port: '3001', url: 'http://localhost:3001', notes: 'cd apps/web && pnpm dev' },
  { service: 'Postgres', port: '5432', url: 'localhost:5432', notes: 'TimescaleDB image; DB name seal' },
  { service: 'Ollama (optional)', port: '11434', url: 'http://localhost:11434', notes: 'When OLLAMA_PROFILE=default' },
] as const;

export function PortsTable() {
  return (
    <div className="not-prose border-border/50 my-6 overflow-x-auto rounded-xl border">
      <table className="w-full min-w-[32rem] text-left text-sm">
        <thead>
          <tr className="border-border/50 bg-muted/40 border-b">
            <th className="text-foreground px-4 py-3 font-semibold">Service</th>
            <th className="text-foreground px-4 py-3 font-semibold">Port</th>
            <th className="text-foreground px-4 py-3 font-semibold">Local URL</th>
            <th className="text-foreground px-4 py-3 font-semibold">Notes</th>
          </tr>
        </thead>
        <tbody className="text-muted-foreground divide-border/40 divide-y">
          {PORTS.map((row) => (
            <tr key={row.service} className="bg-card/30">
              <td className="text-foreground px-4 py-3 font-medium">{row.service}</td>
              <td className="px-4 py-3 font-mono text-xs">{row.port}</td>
              <td className="px-4 py-3">
                <a href={row.url} className="text-primary hover:underline">
                  {row.url}
                </a>
              </td>
              <td className="px-4 py-3">{row.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
