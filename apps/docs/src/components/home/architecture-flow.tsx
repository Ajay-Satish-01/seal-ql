'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import Link from 'next/link';
import {
  MessageSquare,
  Search,
  Server,
  FileJson,
  Sparkles,
  Shield,
  Database,
  BarChart3,
  Radio,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';

type FlowMode = 'query' | 'chat';

type FlowStep = {
  id: string;
  label: string;
  sub: string;
  icon: typeof Server;
  href?: string;
};

const MODES: {
  id: FlowMode;
  label: string;
  icon: typeof Search;
  steps: FlowStep[];
}[] = [
  {
    id: 'query',
    label: 'Analytics query',
    icon: Search,
    steps: [
      {
        id: 'client',
        label: 'SDK / HTTP',
        sub: 'POST /v1/query',
        icon: Server,
        href: '/docs/api-reference',
      },
      {
        id: 'catalog',
        label: 'Data catalog',
        sub: 'YAML descriptions',
        icon: FileJson,
        href: '/docs/data-catalog',
      },
      {
        id: 'planner',
        label: 'Query planner',
        sub: 'LiteLLM + Instructor',
        icon: Sparkles,
      },
      {
        id: 'sql',
        label: 'SQLGlot',
        sub: 'AST validation',
        icon: Shield,
      },
      {
        id: 'db',
        label: 'Executor',
        sub: 'Postgres · DuckDB',
        icon: Database,
      },
      {
        id: 'chart',
        label: 'Vega-Lite',
        sub: 'Chart spec',
        icon: BarChart3,
        href: '/docs/charts-analysis',
      },
    ],
  },
  {
    id: 'chat',
    label: 'Conversational Q&A',
    icon: MessageSquare,
    steps: [
      {
        id: 'client',
        label: 'SDK / HTTP',
        sub: 'POST /v1/chat',
        icon: Server,
        href: '/docs/chat-qa',
      },
      {
        id: 'catalog',
        label: 'Catalog + RAG',
        sub: 'YAML · vector index',
        icon: FileJson,
        href: '/docs/vector-rag',
      },
      {
        id: 'enhance',
        label: 'Enhancement',
        sub: 'Schema · RAG · memory',
        icon: Sparkles,
        href: '/docs/prompt-enhancement',
      },
      {
        id: 'sql',
        label: 'Shared pipeline',
        sub: 'SQL → validate → run',
        icon: Shield,
      },
      {
        id: 'db',
        label: 'Executor',
        sub: 'Results to context',
        icon: Database,
      },
      {
        id: 'stream',
        label: 'SSE answer',
        sub: 'seal.meta + tokens',
        icon: Radio,
        href: '/docs/chat-streaming',
      },
    ],
  },
];

function FlowNode({
  step,
  index,
  active,
  reducedMotion,
}: {
  step: FlowStep;
  index: number;
  active: boolean;
  reducedMotion: boolean;
}) {
  const Icon = step.icon;
  const card = (
    <motion.div
      className={cn(
        'border-border/70 bg-card/80 relative flex min-w-[7.5rem] flex-col items-center rounded-sm border px-3 py-3 backdrop-blur-sm sm:min-w-[8.5rem]',
        active && 'border-primary/70 ring-primary/25 ring-1',
      )}
      animate={
        reducedMotion || !active
          ? undefined
          : {
              boxShadow:
                '0 0 28px -6px color-mix(in oklch, var(--primary) 45%, transparent)',
            }
      }
      transition={{ duration: 0.35 }}
    >
      <div
        className={cn(
          'mb-2 flex h-9 w-9 items-center justify-center rounded-sm transition-colors',
          active ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground',
        )}
      >
        <Icon className="h-4 w-4" />
      </div>
      <span className="font-heading text-center text-xs font-semibold tracking-tight sm:text-sm">
        {step.label}
      </span>
      <span className="text-muted-foreground mt-0.5 text-center font-mono text-[10px] leading-tight sm:text-xs">
        {step.sub}
      </span>
    </motion.div>
  );

  const wrapped = step.href ? (
    <Link href={step.href} className="block transition-transform hover:scale-[1.02]">
      {card}
    </Link>
  ) : (
    card
  );

  return (
    <motion.div
      initial={reducedMotion ? false : { opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.08, duration: 0.45 }}
    >
      {wrapped}
    </motion.div>
  );
}

function FlowConnector({ lit, reducedMotion }: { lit: boolean; reducedMotion: boolean }) {
  return (
    <div className="text-muted-foreground/40 flex shrink-0 items-center px-0.5">
      <motion.div
        className="bg-border h-px w-4 sm:w-6"
        animate={
          reducedMotion
            ? undefined
            : lit
              ? { backgroundColor: 'var(--primary)', scaleX: 1.1 }
              : { backgroundColor: 'var(--border)', scaleX: 1 }
        }
        transition={{ duration: 0.3 }}
      />
      <ChevronRight
        className={cn('h-3.5 w-3.5 shrink-0 transition-colors', lit && 'text-primary')}
      />
    </div>
  );
}

export function ArchitectureFlow() {
  const reducedMotion = useReducedMotion();
  const [mode, setMode] = useState<FlowMode>('chat');
  const [activeStep, setActiveStep] = useState(0);

  const current = MODES.find((m) => m.id === mode) ?? MODES[1];
  const steps = current.steps;

  useEffect(() => {
    if (reducedMotion) return;
    const modeTimer = window.setInterval(() => {
      setMode((m) => (m === 'chat' ? 'query' : 'chat'));
      setActiveStep(0);
    }, 9000);
    return () => window.clearInterval(modeTimer);
  }, [reducedMotion]);

  useEffect(() => {
    if (reducedMotion) return;
    const stepTimer = window.setInterval(() => {
      setActiveStep((s) => (s + 1) % steps.length);
    }, 1400);
    return () => window.clearInterval(stepTimer);
  }, [steps.length, reducedMotion, mode]);

  const flowRow = (
    <div className="flex w-full flex-wrap items-center justify-center gap-y-4 lg:flex-nowrap lg:justify-between">
      {steps.map((step, i) => (
        <div key={`${mode}-${step.id}`} className="flex items-center">
          <FlowNode
            step={step}
            index={i}
            active={i === activeStep}
            reducedMotion={!!reducedMotion}
          />
          {i < steps.length - 1 ? (
            <FlowConnector lit={i === activeStep} reducedMotion={!!reducedMotion} />
          ) : null}
        </div>
      ))}
    </div>
  );

  return (
    <div className="border-border/50 bg-card/30 relative mb-14 overflow-hidden rounded-sm border p-4 sm:p-8">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage: `
            linear-gradient(to right, oklch(0.72 0.16 75 / 0.06) 1px, transparent 1px),
            linear-gradient(to bottom, oklch(0.72 0.16 75 / 0.06) 1px, transparent 1px)
          `,
          backgroundSize: '24px 24px',
        }}
      />

      <div className="relative z-10 mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-primary font-mono text-xs tracking-widest uppercase">Request flow</p>
          <p className="text-muted-foreground mt-1 text-sm">
            Same zero-trust SQL boundary for query and chat — enhancement runs before generation.
          </p>
        </div>
        <div className="border-border/60 bg-background/80 flex rounded-sm border p-1">
          {MODES.map((m) => {
            const Icon = m.icon;
            const selected = mode === m.id;
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => {
                  setMode(m.id);
                  setActiveStep(0);
                }}
                className={cn(
                  'flex items-center gap-2 rounded-sm px-3 py-1.5 text-xs font-medium transition-colors sm:text-sm',
                  selected
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {m.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="relative z-10 hidden lg:block">
        <AnimatePresence mode="wait">
          <motion.div
            key={mode}
            initial={reducedMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={reducedMotion ? undefined : { opacity: 0 }}
            transition={{ duration: 0.35 }}
          >
            {flowRow}
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="relative z-10 lg:hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={mode}
            initial={reducedMotion ? false : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={reducedMotion ? undefined : { opacity: 0, x: 8 }}
            className="flex flex-col items-center gap-2"
          >
            {steps.map((step, i) => (
              <div key={`${mode}-${step.id}-m`} className="flex flex-col items-center">
                <FlowNode
                  step={step}
                  index={i}
                  active={i === activeStep}
                  reducedMotion={!!reducedMotion}
                />
                {i < steps.length - 1 ? (
                  <div
                    className={cn(
                      'my-1 h-6 w-px transition-colors',
                      i === activeStep ? 'bg-primary' : 'bg-border',
                    )}
                  />
                ) : null}
              </div>
            ))}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
