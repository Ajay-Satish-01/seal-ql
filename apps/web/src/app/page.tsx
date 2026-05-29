'use client';

import { Button, buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { ArrowRight, Database, Shield, Zap, Code2 } from 'lucide-react';
import { motion } from 'framer-motion';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } },
};

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center">
      {/* Hero Section */}
      <section className="from-background to-secondary/20 relative flex w-full items-center justify-center overflow-hidden bg-gradient-to-b py-24 lg:py-32 xl:py-48">
        <div className="bg-primary/20 pointer-events-none absolute top-1/2 left-1/2 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-60 blur-[100px]" />

        <motion.div
          className="relative z-10 container flex flex-col items-center px-4 text-center md:px-6"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.div variants={itemVariants}>
            <Badge
              variant="outline"
              className="border-primary/40 text-primary bg-primary/5 mb-6 rounded-full px-4 py-1.5 text-sm"
            >
              v1.0.0 is now live
            </Badge>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="mx-auto mb-8 max-w-4xl text-4xl font-extrabold tracking-tight md:text-6xl lg:text-7xl"
          >
            Query your database with <br className="hidden md:block" />
            <span className="from-primary bg-gradient-to-r to-blue-400 bg-clip-text text-transparent">
              Natural Language
            </span>
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="text-muted-foreground mx-auto mb-10 max-w-[700px] text-xl leading-relaxed md:text-2xl"
          >
            An AI-powered SQL query generation, validation, and visualization SDK enforcing
            zero-trust safety.
          </motion.p>

          <motion.div
            variants={itemVariants}
            className="mx-auto flex w-full max-w-md flex-col justify-center gap-4 sm:flex-row"
          >
            <Link
              href="/docs"
              className={cn(
                buttonVariants({ size: 'lg' }),
                'rounded-full px-8 text-md font-semibold h-12 w-full sm:w-auto shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-all hover:scale-105'
              )}
            >
              Get Started <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <a
              href="https://github.com/your-org/intelligence_connector"
              target="_blank"
              rel="noreferrer"
              className={cn(
                buttonVariants({ variant: 'outline', size: 'lg' }),
                'rounded-full px-8 text-md font-semibold border-border/50 hover:bg-secondary h-12 w-full sm:w-auto transition-all hover:scale-105'
              )}
            >
              View on GitHub
            </a>
          </motion.div>
        </motion.div>
      </section>

      {/* Features Grid */}
      <section className="bg-background border-border/40 relative z-20 w-full border-t py-20">
        <motion.div
          className="container mx-auto px-4 md:px-6"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-100px' }}
          variants={containerVariants}
        >
          <motion.div variants={itemVariants} className="mb-16 text-center">
            <h2 className="mb-4 text-3xl font-bold md:text-4xl">Enterprise-Grade Architecture</h2>
            <p className="text-muted-foreground mx-auto max-w-[600px] text-lg">
              Built with security, precision, and performance as first-class citizens.
            </p>
          </motion.div>

          <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            <motion.div variants={itemVariants} whileHover={{ y: -5 }} className="h-full">
              <Card className="bg-card/40 border-border/50 hover:border-primary/50 hover:shadow-primary/5 h-full shadow-none backdrop-blur-md transition-colors hover:shadow-xl">
                <CardHeader>
                  <div className="bg-primary/10 mb-4 flex h-12 w-12 items-center justify-center rounded-lg">
                    <Shield className="text-primary h-6 w-6" />
                  </div>
                  <CardTitle>Zero-Trust Safety</CardTitle>
                  <CardDescription className="mt-2 text-base">
                    Strict AST parsing using SQLGlot to block destructive statements and enforce
                    limits.
                  </CardDescription>
                </CardHeader>
              </Card>
            </motion.div>

            <motion.div variants={itemVariants} whileHover={{ y: -5 }} className="h-full">
              <Card className="bg-card/40 border-border/50 hover:border-primary/50 hover:shadow-primary/5 h-full shadow-none backdrop-blur-md transition-colors hover:shadow-xl">
                <CardHeader>
                  <div className="bg-primary/10 mb-4 flex h-12 w-12 items-center justify-center rounded-lg">
                    <Database className="text-primary h-6 w-6" />
                  </div>
                  <CardTitle>Semantic Layer</CardTitle>
                  <CardDescription className="mt-2 text-base">
                    Map raw schema structures to business logic with declarative YAML models.
                  </CardDescription>
                </CardHeader>
              </Card>
            </motion.div>

            <motion.div variants={itemVariants} whileHover={{ y: -5 }} className="h-full">
              <Card className="bg-card/40 border-border/50 hover:border-primary/50 hover:shadow-primary/5 h-full shadow-none backdrop-blur-md transition-colors hover:shadow-xl">
                <CardHeader>
                  <div className="bg-primary/10 mb-4 flex h-12 w-12 items-center justify-center rounded-lg">
                    <Zap className="text-primary h-6 w-6" />
                  </div>
                  <CardTitle>Dialect Intrinsic</CardTitle>
                  <CardDescription className="mt-2 text-base">
                    Highly optimized execution for Postgres (TimescaleDB) and DuckDB.
                  </CardDescription>
                </CardHeader>
              </Card>
            </motion.div>

            <motion.div variants={itemVariants} whileHover={{ y: -5 }} className="h-full">
              <Card className="bg-card/40 border-border/50 hover:border-primary/50 hover:shadow-primary/5 h-full shadow-none backdrop-blur-md transition-colors hover:shadow-xl">
                <CardHeader>
                  <div className="bg-primary/10 mb-4 flex h-12 w-12 items-center justify-center rounded-lg">
                    <Code2 className="text-primary h-6 w-6" />
                  </div>
                  <CardTitle>Visual Generation</CardTitle>
                  <CardDescription className="mt-2 text-base">
                    Automatically produces precise Vega-Lite visual schemas based on return data.
                  </CardDescription>
                </CardHeader>
              </Card>
            </motion.div>
          </div>
        </motion.div>
      </section>
    </main>
  );
}
