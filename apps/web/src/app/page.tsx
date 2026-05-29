import { Button } from '@/components/ui/button';
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import { ArrowRight, Database, Shield, Zap, Code2 } from 'lucide-react';

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center">
      {/* Hero Section */}
      <section className="from-background to-secondary/20 relative flex w-full items-center justify-center overflow-hidden bg-gradient-to-b py-24 lg:py-32 xl:py-48">
        {/* Abstract Background Shapes */}
        <div className="bg-primary/20 pointer-events-none absolute top-1/2 left-1/2 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-60 blur-[100px]" />

        <div className="relative z-10 container flex flex-col items-center px-4 text-center md:px-6">
          <Badge
            variant="outline"
            className="border-primary/40 text-primary bg-primary/5 mb-6 rounded-full px-4 py-1.5 text-sm"
          >
            v1.0.0 is now live
          </Badge>
          <h1 className="mx-auto mb-8 max-w-4xl text-4xl font-extrabold tracking-tight md:text-6xl lg:text-7xl">
            Query your database with <br className="hidden md:block" />
            <span className="from-primary bg-gradient-to-r to-blue-400 bg-clip-text text-transparent">
              Natural Language
            </span>
          </h1>
          <p className="text-muted-foreground mx-auto mb-10 max-w-[700px] text-xl leading-relaxed md:text-2xl">
            An AI-powered SQL query generation, validation, and visualization SDK enforcing
            zero-trust safety.
          </p>
          <div className="mx-auto flex w-full max-w-md flex-col justify-center gap-4 sm:flex-row">
            <Button
              asChild
              size="lg"
              className="text-md shadow-primary/25 hover:shadow-primary/40 h-12 w-full rounded-full px-8 font-semibold shadow-lg transition-all sm:w-auto"
            >
              <Link href="/docs">
                Get Started <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="lg"
              className="text-md border-border/50 hover:bg-secondary h-12 w-full rounded-full px-8 font-semibold transition-all sm:w-auto"
            >
              <a
                href="https://github.com/your-org/intelligence_connector"
                target="_blank"
                rel="noreferrer"
              >
                View on GitHub
              </a>
            </Button>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="bg-background border-border/40 relative z-20 w-full border-t py-20">
        <div className="container mx-auto px-4 md:px-6">
          <div className="mb-16 text-center">
            <h2 className="mb-4 text-3xl font-bold md:text-4xl">Enterprise-Grade Architecture</h2>
            <p className="text-muted-foreground mx-auto max-w-[600px] text-lg">
              Built with security, precision, and performance as first-class citizens.
            </p>
          </div>

          <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card className="bg-card/40 border-border/50 hover:border-primary/50 hover:shadow-primary/5 backdrop-blur-md transition-all hover:-translate-y-1 hover:shadow-xl">
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

            <Card className="bg-card/40 border-border/50 hover:border-primary/50 hover:shadow-primary/5 backdrop-blur-md transition-all hover:-translate-y-1 hover:shadow-xl">
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

            <Card className="bg-card/40 border-border/50 hover:border-primary/50 hover:shadow-primary/5 backdrop-blur-md transition-all hover:-translate-y-1 hover:shadow-xl">
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

            <Card className="bg-card/40 border-border/50 hover:border-primary/50 hover:shadow-primary/5 backdrop-blur-md transition-all hover:-translate-y-1 hover:shadow-xl">
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
          </div>
        </div>
      </section>
    </main>
  );
}
