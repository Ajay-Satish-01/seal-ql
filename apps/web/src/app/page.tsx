'use client';

import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { ArrowRight, Database, Shield, Zap, Code2, Container, KeyRound } from 'lucide-react';
import { SealLogo } from '@/components/seal-logo';
import { motion, Variants } from 'framer-motion';
import { SITE } from '@/lib/constants';

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.15 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } },
};

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <section className="hero-grid border-border/40 relative flex w-full items-center justify-center overflow-hidden border-b py-24 lg:py-36">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-amber-500/5 via-transparent to-teal-500/5" />

        <motion.div
          className="relative z-10 container mx-auto max-w-5xl px-4 md:px-6"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div variants={itemVariants} className="mb-6 flex items-center gap-4">
            <SealLogo size={56} className="hidden sm:block" />
            <Badge
              variant="outline"
              className="border-primary/50 text-primary rounded-sm px-3 py-1 font-mono text-xs tracking-widest uppercase"
            >
              Seal · Open source · Image-first
            </Badge>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="font-heading mb-6 max-w-3xl text-4xl leading-[1.1] font-semibold tracking-tight md:text-6xl"
          >
            <span className="sm:hidden">Seal — </span>
            Natural language to <span className="text-primary">validated SQL</span> and charts
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="text-muted-foreground mb-10 max-w-2xl text-lg leading-relaxed md:text-xl"
          >
            Self-host with Docker. Conversational Q&A with RAG, optional charts, and agent-tool
            compatible APIs. Every query passes a zero-trust SQLGlot boundary — see{' '}
            <Link href="/docs/chat-qa" className="text-primary underline-offset-4 hover:underline">
              Chat &amp; Q&A
            </Link>
            .
          </motion.p>

          <motion.div variants={itemVariants} className="flex flex-col flex-wrap gap-3 sm:flex-row">
            <Link
              href="/demo"
              className={cn(buttonVariants({ size: 'lg' }), 'rounded-sm px-6 font-semibold')}
            >
              Try Demo <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link
              href="/docs/self-hosting"
              className={cn(
                buttonVariants({ variant: 'secondary', size: 'lg' }),
                'rounded-sm px-6 font-semibold',
              )}
            >
              <Container className="mr-2 h-4 w-4" />
              Run with Docker
            </Link>
            <Link
              href="/docs/integration-guide#sdk"
              className={cn(
                buttonVariants({ variant: 'outline', size: 'lg' }),
                'rounded-sm px-6 font-semibold',
              )}
            >
              Install SDK
            </Link>
          </motion.div>

          <motion.p variants={itemVariants} className="text-muted-foreground mt-6 text-sm">
            <Link
              href="/docs/contributing"
              className="hover:text-primary underline-offset-4 hover:underline"
            >
              Develop from source
            </Link>{' '}
            ·{' '}
            <a
              href={SITE.github}
              target="_blank"
              rel="noreferrer"
              className="hover:text-primary underline-offset-4 hover:underline"
            >
              GitHub
            </a>
          </motion.p>
        </motion.div>
      </section>

      <section className="container mx-auto max-w-6xl px-4 py-20 md:px-6">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={containerVariants}
        >
          <motion.div variants={itemVariants} className="mb-12 text-center">
            <h2 className="font-heading text-3xl font-semibold md:text-4xl">
              Built for production data apps
            </h2>
            <p className="text-muted-foreground mx-auto mt-3 max-w-xl">
              Audit the validator on GitHub. Deploy from Docker Hub. Ship in minutes.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {[
              {
                icon: Shield,
                title: 'Zero-Trust Safety',
                desc: 'SQLGlot AST validation blocks destructive SQL and enforces row limits.',
              },
              {
                icon: KeyRound,
                title: 'API Key Auth',
                desc: 'Protect /v1/* with X-API-Key. Your backend holds the secret — not end-user browsers.',
                href: '/docs/authentication',
              },
              {
                icon: Database,
                title: 'Deep Introspection',
                desc: 'Postgres, TimescaleDB hypertables, materialized views, and DuckDB.',
              },
              {
                icon: Zap,
                title: 'Self-Healing SQL',
                desc: 'Dialect errors feed back into the planner for automatic repair.',
              },
              {
                icon: Code2,
                title: 'Vega-Lite Charts',
                desc: 'Chart engine returns typed specs your UI can render immediately.',
              },
            ].map(({ icon: Icon, title, desc, href }) => (
              <motion.div key={title} variants={itemVariants}>
                <Card className="border-border/60 bg-card/60 h-full rounded-sm backdrop-blur-sm">
                  <CardHeader>
                    <div className="bg-primary/10 mb-3 flex h-10 w-10 items-center justify-center rounded-sm">
                      <Icon className="text-primary h-5 w-5" />
                    </div>
                    <CardTitle className="font-heading text-lg">
                      {href ? (
                        <Link href={href} className="hover:text-primary transition-colors">
                          {title}
                        </Link>
                      ) : (
                        title
                      )}
                    </CardTitle>
                    <CardDescription className="text-base">{desc}</CardDescription>
                  </CardHeader>
                </Card>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>
    </main>
  );
}
