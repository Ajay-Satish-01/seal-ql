import { CodeBlock } from '@/components/code-block';
import { Callout } from '@/components/docs/callout';
import { ParamTable } from '@/components/docs/param-table';

const LITELLM_DOCS = 'https://docs.litellm.ai/docs/providers';

/** Shared LLM setup docs — mirrors `.env.example` and `intelligence_core.settings`. */
export function LlmConfigSection() {
  return (
    <section id="llm-configuration" className="not-prose scroll-mt-24">
      <h2 className="text-foreground mt-10 mb-4 text-2xl font-bold">LLM configuration</h2>
      <p className="text-muted-foreground mb-6 leading-relaxed">
        The API routes all planner calls through{' '}
        <a href={LITELLM_DOCS} className="text-primary hover:underline" target="_blank" rel="noreferrer">
          LiteLLM
        </a>
        . You choose the provider with <code className="text-foreground">LLM_MODEL</code> using
        LiteLLM&apos;s <code className="text-foreground">provider/model</code> naming, and you
        authenticate with standard provider API key environment variables.
      </p>

      <h3 className="text-foreground mb-3 text-lg font-semibold">Ollama vs cloud</h3>
      <p className="text-muted-foreground mb-4 leading-relaxed">
        <code className="text-foreground">OLLAMA_PROFILE</code> controls both Docker Compose (whether
        the Ollama container starts) and API routing (local Ollama vs cloud).
      </p>
      <ParamTable
        title="OLLAMA_PROFILE"
        rows={[
          {
            name: 'default (or omit)',
            type: 'profile',
            description: 'Starts Ollama in compose. Use ollama/… model ids and LLM_BASE_URL.',
          },
          {
            name: 'disabled',
            type: 'profile',
            description:
              'Skips Ollama. Use cloud model ids (gemini/, openai/, anthropic/, …) and an API key.',
          },
        ]}
      />

      <h3 className="text-foreground mt-10 mb-3 text-lg font-semibold">LiteLLM model ids</h3>
      <p className="text-muted-foreground mb-4 leading-relaxed">
        Set <code className="text-foreground">LLM_MODEL</code> to the LiteLLM model string for your
        provider. The general pattern is{' '}
        <code className="text-foreground">provider/model-name</code> (see{' '}
        <a href={LITELLM_DOCS} className="text-primary hover:underline" target="_blank" rel="noreferrer">
          LiteLLM providers
        </a>
        ).
      </p>
      <ParamTable
        title="Common LLM_MODEL values"
        rows={[
          {
            name: 'ollama/llama3.2:1b',
            type: 'local',
            description: 'Ollama (requires OLLAMA_PROFILE default and LLM_BASE_URL).',
          },
          {
            name: 'gemini/gemini-1.5-flash',
            type: 'cloud',
            description: 'Google Gemini (requires OLLAMA_PROFILE=disabled).',
          },
          {
            name: 'openai/gpt-4o-mini',
            type: 'cloud',
            description: 'OpenAI (requires OLLAMA_PROFILE=disabled).',
          },
          {
            name: 'anthropic/claude-3-5-sonnet-20241022',
            type: 'cloud',
            description: 'Anthropic Claude (requires OLLAMA_PROFILE=disabled).',
          },
        ]}
      />

      <h3 className="text-foreground mt-10 mb-3 text-lg font-semibold">API keys (LiteLLM)</h3>
      <p className="text-muted-foreground mb-4 leading-relaxed">
        LiteLLM reads provider credentials from the environment. You can set a single{' '}
        <code className="text-foreground">LLM_API_KEY</code> for any cloud provider, or use the
        provider-specific variables LiteLLM documents for each model family.
      </p>
      <ParamTable
        title="Cloud credentials"
        rows={[
          {
            name: 'LLM_API_KEY',
            type: 'string',
            description: 'Generic key passed through to LiteLLM for the configured model.',
          },
          {
            name: 'GEMINI_API_KEY',
            type: 'string',
            description: 'Used when LLM_MODEL starts with gemini/ (LiteLLM default for Gemini).',
          },
          {
            name: 'OPENAI_API_KEY',
            type: 'string',
            description: 'Used when LLM_MODEL starts with openai/.',
          },
          {
            name: 'ANTHROPIC_API_KEY',
            type: 'string',
            description: 'Used when LLM_MODEL starts with anthropic/.',
          },
        ]}
      />

      <h3 className="text-foreground mt-10 mb-3 text-lg font-semibold">Option A — Ollama (default)</h3>
      <Callout variant="success" title="No API key required">
        Omit <code>OLLAMA_PROFILE</code> or set <code>default</code>. Run{' '}
        <code>make up</code> (or compose with profile <code>default</code>) so the Ollama service
        starts. Point <code>LLM_BASE_URL</code> at the Ollama HTTP API inside the stack.
      </Callout>
      <CodeBlock
        language="bash"
        code={`# .env — local Ollama
LLM_MODEL=ollama/llama3.2:1b
LLM_BASE_URL=http://ollama:11434`}
      />

      <h3 className="text-foreground mt-10 mb-3 text-lg font-semibold">
        Option B — Cloud (Gemini, OpenAI, Anthropic, …)
      </h3>
      <Callout variant="info" title="OLLAMA_PROFILE=disabled">
        Disables the Ollama container and routes planner calls to your cloud model. Do not set{' '}
        <code>LLM_BASE_URL</code>.
      </Callout>
      <CodeBlock
        language="bash"
        code={`# .env — cloud (LiteLLM)
OLLAMA_PROFILE=disabled
LLM_MODEL=gemini/gemini-1.5-flash
LLM_API_KEY=your-key-here

# Equivalent: provider-specific key (LiteLLM convention)
# LLM_MODEL=gemini/gemini-1.5-flash
# GEMINI_API_KEY=your-key-here

# OpenAI example:
# LLM_MODEL=openai/gpt-4o-mini
# OPENAI_API_KEY=sk-...

# Anthropic example:
# LLM_MODEL=anthropic/claude-3-5-sonnet-20241022
# ANTHROPIC_API_KEY=sk-ant-...`}
      />

      <p className="text-muted-foreground mt-6 text-sm leading-relaxed">
        On startup the API logs the active mode and warns if{' '}
        <code className="text-foreground">LLM_MODEL</code> does not match{' '}
        <code className="text-foreground">OLLAMA_PROFILE</code> (for example a{' '}
        <code className="text-foreground">gemini/</code> model without{' '}
        <code className="text-foreground">OLLAMA_PROFILE=disabled</code>).
      </p>

      <h3 className="text-foreground mt-8 mb-3 text-lg font-semibold">Apply and restart</h3>
      <CodeBlock
        language="bash"
        code={`docker compose -f docker-compose.example.yml up -d --force-recreate api`}
      />
    </section>
  );
}
