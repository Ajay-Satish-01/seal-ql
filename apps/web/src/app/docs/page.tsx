export default function DocsPage() {
  return (
    <div className="container mx-auto max-w-4xl px-4 py-12">
      <h1 className="mb-6 text-4xl font-bold">Documentation</h1>
      <p className="text-muted-foreground mb-8 text-xl">
        Welcome to the Intelligence Connector documentation.
      </p>

      <div className="prose prose-blue dark:prose-invert max-w-none">
        <h2>Quick Start</h2>
        <p>Ensure you have Docker and uv installed.</p>
        <pre className="bg-muted overflow-x-auto rounded-lg p-4">
          <code>make up</code>
        </pre>

        <h3 className="mt-8">Python SDK Setup</h3>
        <pre className="bg-muted overflow-x-auto rounded-lg p-4">
          <code>uv sync --all-packages --all-extras</code>
        </pre>

        <h3 className="mt-8">TypeScript SDK Setup</h3>
        <pre className="bg-muted overflow-x-auto rounded-lg p-4">
          <code>cd sdks/typescript && pnpm install</code>
        </pre>
      </div>
    </div>
  );
}
