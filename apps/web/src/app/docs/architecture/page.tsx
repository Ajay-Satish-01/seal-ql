'use client';

import { PageHeader } from '@/components/page-header';
import { ArrowDown, Database, Server, Cpu, FileJson, Layout } from 'lucide-react';
import { motion } from 'framer-motion';

function ArchitectureNode({ icon: Icon, title, description, delay = 0 }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-card/40 border-border/50 mx-auto flex w-full max-w-sm flex-col items-center rounded-2xl border p-6 shadow-sm backdrop-blur-md"
    >
      <div className="bg-primary/10 mb-4 flex h-14 w-14 items-center justify-center rounded-xl">
        <Icon className="text-primary h-7 w-7" />
      </div>
      <h3 className="mb-2 text-center text-xl font-bold">{title}</h3>
      <p className="text-muted-foreground text-center text-sm leading-relaxed">{description}</p>
    </motion.div>
  );
}

function Arrow({ delay = 0 }: { delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay }}
      className="my-4 flex justify-center"
    >
      <ArrowDown className="text-border h-8 w-8 animate-bounce" />
    </motion.div>
  );
}

export default function ArchitecturePage() {
  return (
    <div className="max-w-4xl pb-20">
      <PageHeader
        title="System Architecture"
        description="Understanding the data flow from natural language to precise execution."
      />

      <div className="mt-12 flex w-full flex-col items-center">
        <ArchitectureNode
          icon={Layout}
          title="1. Frontend / SDKs"
          description="TypeScript or Python Clients. Sends natural language prompts and schema context over HTTP/gRPC."
          delay={0.1}
        />

        <Arrow delay={0.2} />

        <ArchitectureNode
          icon={Server}
          title="2. API Gateway"
          description="FastAPI / Uvicorn server orchestrating the request pipeline."
          delay={0.3}
        />

        <Arrow delay={0.4} />

        <ArchitectureNode
          icon={Cpu}
          title="3. Query Planner (LLM)"
          description="LiteLLM + Instructor + Ollama. Translates the prompt to SQL via schema semantic mapping."
          delay={0.5}
        />

        <Arrow delay={0.6} />

        <ArchitectureNode
          icon={FileJson}
          title="4. SQL Validator"
          description="SQLGlot AST validation ensures absolute zero-trust safety. Blocks destructive mutations and unbounded SELECTs."
          delay={0.7}
        />

        <Arrow delay={0.8} />

        <ArchitectureNode
          icon={Database}
          title="5. Database Executor"
          description="Safely executes the validated AST on DuckDB or Postgres (TimescaleDB)."
          delay={0.9}
        />
      </div>
    </div>
  );
}
