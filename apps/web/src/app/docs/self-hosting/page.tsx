import { PageHeader } from '@/components/page-header';
import { CodeBlock } from '@/components/code-block';

export default function SelfHostingPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Self-Hosting with Docker"
        description="Deploy Intelligence Connector on your own infrastructure using Docker Compose."
      />

      <div className="prose prose-slate dark:prose-invert text-muted-foreground max-w-none leading-relaxed">
        <p>
          Intelligence Connector is built to be run fully self-hosted. We provide a complete{' '}
          <code>docker-compose.yml</code> stack that spins up the API Gateway, a Postgres database,
          and a local Ollama instance out-of-the-box.
        </p>

        <h2>Quick Start</h2>
        <p>
          Ensure you have Docker and Docker Compose installed. Clone the repository and simply run:
        </p>
        <CodeBlock language="bash" code="make up" />

        <p>
          This command builds the images and starts the containers in detached mode. You will have:
        </p>
        <ul>
          <li>
            <strong>API Gateway:</strong> <code>http://localhost:8000</code>
          </li>
          <li>
            <strong>Postgres:</strong> <code>localhost:5432</code>
          </li>
          <li>
            <strong>Ollama (Local LLM):</strong> <code>http://localhost:11434</code>
          </li>
        </ul>

        <hr />

        <h2>Environment Configuration</h2>
        <p>
          You can configure the system by setting environment variables before running{' '}
          <code>make up</code> or by creating a <code>.env</code> file in the root directory.
        </p>

        <div className="my-6">
          <table className="border-border/50 w-full border-collapse border text-left text-sm">
            <thead className="bg-muted text-foreground">
              <tr>
                <th className="border-border/50 border p-2">Variable</th>
                <th className="border-border/50 border p-2">Default</th>
                <th className="border-border/50 border p-2">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border-border/50 text-primary border p-2 font-mono">DATABASE_URL</td>
                <td className="border-border/50 border p-2 font-mono text-xs">
                  postgresql+asyncpg://postgres:postgres@postgres:5432/intelligence_connector
                </td>
                <td className="border-border/50 border p-2">
                  The database string for introspection and execution.
                </td>
              </tr>
              <tr>
                <td className="border-border/50 text-primary border p-2 font-mono">LLM_TYPE</td>
                <td className="border-border/50 border p-2 font-mono text-xs">local</td>
                <td className="border-border/50 border p-2">
                  Type of LLM (<code>local</code>, <code>gemini</code>, <code>openai</code>, etc.)
                </td>
              </tr>
              <tr>
                <td className="border-border/50 text-primary border p-2 font-mono">LLM_MODEL</td>
                <td className="border-border/50 border p-2 font-mono text-xs">
                  ollama/llama3.2:1b
                </td>
                <td className="border-border/50 border p-2">
                  The model identifier to use for the planner.
                </td>
              </tr>
              <tr>
                <td className="border-border/50 text-primary border p-2 font-mono">
                  GEMINI_API_KEY
                </td>
                <td className="border-border/50 border p-2 font-mono text-xs"></td>
                <td className="border-border/50 border p-2">
                  Required if using Google Gemini models.
                </td>
              </tr>
              <tr>
                <td className="border-border/50 text-primary border p-2 font-mono">MAX_ROWS</td>
                <td className="border-border/50 border p-2 font-mono text-xs">10000</td>
                <td className="border-border/50 border p-2">Hard limit for pagination safety.</td>
              </tr>
            </tbody>
          </table>
        </div>

        <hr />

        <h2>Configuring LLM Providers</h2>
        <p>
          By default, the stack uses a local Ollama container. You can easily switch to managed
          cloud providers like Google Gemini if you want faster or more powerful models.
        </p>

        <h3>Option A: Default Local Ollama</h3>
        <p>
          No configuration is required. The Docker Compose file will automatically pull and serve{' '}
          <code>llama3.2:1b</code>.
        </p>
        <CodeBlock
          language="bash"
          code="export LLM_TYPE=local
export LLM_MODEL=ollama/llama3.2:1b
make up"
        />

        <h3>Option B: Using Google Gemini</h3>
        <p>
          To use Gemini (e.g., Gemini 1.5 Flash), pass your API key and update the model variables:
        </p>
        <CodeBlock
          language="bash"
          code="export LLM_TYPE=gemini
export LLM_MODEL=gemini/gemini-1.5-flash
export GEMINI_API_KEY=your_api_key_here
make up"
        />

        <hr />

        <h2>Using the Gateway</h2>
        <p>
          Once your docker containers are running, you can prompt the system directly using{' '}
          <code>curl</code> or our SDKs:
        </p>
        <CodeBlock
          language="bash"
          code={`curl -X POST http://localhost:8000/query \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Count the number of active users"}'`}
        />

        <p>
          The gateway will introspect the database, generate the SQL, validate the AST, execute the
          query, and return the final data payload back to you.
        </p>
      </div>
    </div>
  );
}
