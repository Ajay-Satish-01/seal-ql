import { PageHeader } from "@/components/page-header";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { ArrowRight, Database, Shield, Zap, BarChart } from "lucide-react";

export default function DocsPage() {
  return (
    <div className="max-w-3xl">
      <PageHeader
        title="What is Intelligence Connector?"
        description="A unified, secure, and intelligent gateway between Natural Language and your Databases."
      />

      <div className="prose prose-slate dark:prose-invert max-w-none text-muted-foreground leading-relaxed">
        <p className="text-lg">
          Intelligence Connector is a comprehensive SDK and API gateway designed to streamline and secure natural language database querying for modern AI applications.
          It serves as the critical safety and translation layer between your LLMs and your relational databases.
        </p>

        <h3 className="text-xl font-semibold text-foreground mt-8 mb-4">Why use Intelligence Connector?</h3>
        <p>
          Building reliable text-to-SQL applications is notoriously difficult. Developers face hallucinated schemas, destructive SQL injections (`DROP TABLE`), malformed syntax, and a lack of visual data representation.
          Intelligence Connector solves these problems systematically:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8 mb-8 not-prose">
          <div className="border border-border/50 rounded-xl p-5 bg-card text-card-foreground shadow-sm">
            <Shield className="h-8 w-8 text-primary mb-3" />
            <h4 className="font-semibold text-lg mb-2">Zero-Trust Safety</h4>
            <p className="text-sm text-muted-foreground">Every generated SQL query is parsed into an AST via SQLGlot. Destructive operations (DROP, DELETE) are explicitly blocked before they ever touch the database.</p>
          </div>
          <div className="border border-border/50 rounded-xl p-5 bg-card text-card-foreground shadow-sm">
            <Zap className="h-8 w-8 text-primary mb-3" />
            <h4 className="font-semibold text-lg mb-2">Auto-Repair Loop</h4>
            <p className="text-sm text-muted-foreground">If an LLM hallucinates a bad column or syntax, the gateway captures the database exception and dynamically re-prompts the LLM to repair the query automatically.</p>
          </div>
          <div className="border border-border/50 rounded-xl p-5 bg-card text-card-foreground shadow-sm">
            <Database className="h-8 w-8 text-primary mb-3" />
            <h4 className="font-semibold text-lg mb-2">Schema Introspection</h4>
            <p className="text-sm text-muted-foreground">We actively fetch your database schema (Postgres, DuckDB) and inject only the relevant DDL and Semantic Models into the LLM context to save tokens and improve accuracy.</p>
          </div>
          <div className="border border-border/50 rounded-xl p-5 bg-card text-card-foreground shadow-sm">
            <BarChart className="h-8 w-8 text-primary mb-3" />
            <h4 className="font-semibold text-lg mb-2">Instant Visualization</h4>
            <p className="text-sm text-muted-foreground">Every executed query returns a fully-typed Vega-Lite JSON specification, allowing your frontend to instantly render beautiful, dynamic charts without manual processing.</p>
          </div>
        </div>

        <p>
          Whether you are building an internal analytics copilot or a customer-facing data dashboard, Intelligence Connector provides the SDKs and APIs to get to production safely.
        </p>

        <div className="mt-10 flex gap-4 not-prose">
          <Link
            href="/docs/features"
            className={cn(buttonVariants({ variant: "outline", size: "lg" }), "rounded-full")}
          >
            Explore Features
          </Link>
          <Link
            href="/docs/quickstart"
            className={cn(buttonVariants({ size: "lg" }), "rounded-full")}
          >
            Quickstart <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
