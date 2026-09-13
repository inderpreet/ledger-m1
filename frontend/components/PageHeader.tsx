export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="font-serif text-3xl tracking-tight text-ink">{title}</h1>
        {subtitle ? <p className="mt-1 text-sm text-ink/60">{subtitle}</p> : null}
      </div>
      {action}
    </header>
  );
}
