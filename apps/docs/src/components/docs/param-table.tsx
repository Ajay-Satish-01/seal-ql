interface ParamRow {
  name: string;
  type: string;
  required?: boolean;
  description: string;
}

interface ParamTableProps {
  title?: string;
  rows: ParamRow[];
}

export function ParamTable({ title, rows }: ParamTableProps) {
  return (
    <div className="my-6">
      {title ? <h4 className="text-foreground mb-3 text-sm font-semibold">{title}</h4> : null}
      <table className="border-border/50 w-full border-collapse border text-left text-sm">
        <thead className="bg-muted/80">
          <tr>
            <th className="border-border/50 border p-2">Field</th>
            <th className="border-border/50 border p-2">Type</th>
            <th className="border-border/50 border p-2">Description</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name}>
              <td className="border-border/50 border p-2 font-mono text-xs">
                {row.name}
                {row.required ? <span className="text-destructive ml-1">*</span> : null}
              </td>
              <td className="border-border/50 text-muted-foreground border p-2 font-mono text-xs">
                {row.type}
              </td>
              <td className="border-border/50 border p-2">{row.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
