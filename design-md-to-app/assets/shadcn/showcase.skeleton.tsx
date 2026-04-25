// Skeleton for app/showcase/page.tsx (shadcn flow).
// Replace the SAMPLE_* arrays with values pulled from the parsed DESIGN.md.
// Names should match the DESIGN.md tokens 1:1 — that's the whole point of the
// page: confirm the mapping is correct.
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

// One entry per colors.* — name + Tailwind class that resolves to the CSS var.
const COLOR_SWATCHES: { name: string; cls: string; on?: string }[] = [
  { name: "background",     cls: "bg-background",     on: "text-foreground" },
  { name: "primary",        cls: "bg-primary",        on: "text-primary-foreground" },
  { name: "secondary",      cls: "bg-secondary",      on: "text-secondary-foreground" },
  { name: "accent",         cls: "bg-accent",         on: "text-accent-foreground" },
  { name: "muted",          cls: "bg-muted",          on: "text-muted-foreground" },
  { name: "card",           cls: "bg-card",           on: "text-card-foreground" },
  { name: "destructive",    cls: "bg-destructive",    on: "text-destructive-foreground" },
  // … add one per defined token
];

// One entry per typography.<level> — name + Tailwind classes.
const TYPE_LADDER: { name: string; cls: string; sample: string }[] = [
  // { name: "headline-xl", cls: "font-display text-headline-xl", sample: "Lorem totality" },
  // { name: "headline-lg", cls: "font-display text-headline-lg", sample: "Heading lg" },
  // { name: "body-md",     cls: "font-sans text-body-md",        sample: "The quick brown fox jumps over the lazy dog." },
];

// One entry per defined components.* — render the actual component with the
// real classes/variants so the user sees the configured look.
const COMPONENT_DEMOS: { name: string; node: React.ReactNode }[] = [
  // { name: "button-primary",   node: <Button>Primary</Button> },
  // { name: "button-secondary", node: <Button variant="outline">Secondary</Button> },
  // { name: "input-field",      node: <Input placeholder="Type here" /> },
  // { name: "badge-celestial",  node: <Badge variant="celestial">Total Eclipse</Badge> },
];

export default function Showcase() {
  return (
    <main className="container mx-auto py-16 space-y-16">
      <header className="space-y-2">
        <h1 className="font-display text-headline-xl">Design system showcase</h1>
        <p className="text-muted-foreground">
          Generated from DESIGN.md. Use this page to verify tokens render correctly.
        </p>
      </header>

      <section className="space-y-4">
        <h2 className="font-display text-headline-md">Colors</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          {COLOR_SWATCHES.map((s) => (
            <div
              key={s.name}
              className={`${s.cls} ${s.on ?? ""} h-24 rounded-md p-3 flex items-end text-xs font-mono border border-border`}
            >
              {s.name}
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="font-display text-headline-md">Typography</h2>
        <ul className="space-y-6">
          {TYPE_LADDER.map((t) => (
            <li key={t.name}>
              <span className="text-xs font-mono text-muted-foreground">{t.name}</span>
              <div className={t.cls}>{t.sample}</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-4">
        <h2 className="font-display text-headline-md">Components</h2>
        <div className="grid sm:grid-cols-2 gap-6">
          {COMPONENT_DEMOS.map((c) => (
            <Card key={c.name}>
              <CardHeader>
                <CardTitle className="text-sm font-mono">{c.name}</CardTitle>
              </CardHeader>
              <CardContent>{c.node}</CardContent>
            </Card>
          ))}
        </div>
      </section>
    </main>
  );
}
