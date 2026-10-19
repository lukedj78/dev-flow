import { cn } from "@/lib/utils";

// The rule-10 stagger: no opacity-0 on the element — `fill-mode-both` holds the `from` frame during the delay.
export function FeatureList({ items }: { items: { id: string; body: string }[] }) {
  return items.map((item, i) => (
    <div key={item.id}
         className="animate-in fade-in slide-in-from-bottom-4 fill-mode-both motion-reduce:animate-none"
         style={{ animationDelay: `${i * 60}ms` }}>
      {item.body}
    </div>
  ));
}

export function Reveal({ children }: { children: React.ReactNode }) {
  return (
    <p className={cn("opacity-0 motion-safe:animate-[fade-up_600ms_ease-out_forwards]", "motion-reduce:opacity-100")}>
      {children}
    </p>
  );
}

// shadcn primitives animate on state with prefixed variants — not an entrance hidden at rest.
export const dialog = "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 group-hover:opacity-0";
