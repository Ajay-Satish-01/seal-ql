interface PageHeaderProps {
  title: string;
  description: string;
}

/** Server-friendly header — avoids framer-motion on every doc page (faster dev compile). */
export function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <div className="border-border/40 mb-10 border-b pb-10">
      <h1 className="font-heading mb-4 text-4xl font-extrabold tracking-tight md:text-5xl">
        {title}
      </h1>
      <p className="text-muted-foreground text-xl">{description}</p>
    </div>
  );
}
