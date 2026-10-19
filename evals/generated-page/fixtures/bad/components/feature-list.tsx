import { cn } from "@/lib/utils";

// tw-animate-css's `enter` keyframe has only a `from` frame: opacity-0 + animate-in fades 0 → 0. Hidden for everyone.
export function FeatureList({ items }: { items: { id: string; body: string }[] }) {
  return items.map((item, i) => (
    <div key={item.id} className="opacity-0 animate-in fade-in slide-in-from-bottom-4 fill-mode-forwards"
         style={{ animationDelay: `${i * 60}ms` }}>
      {item.body}
    </div>
  ));
}

// A custom keyframe that ends at opacity 1 works — but with no motion-reduce:opacity-100 it stays hidden
// for a reduced-motion user once the animation is removed.
export function Reveal({ children }: { children: React.ReactNode }) {
  return <p className={cn("opacity-0", "motion-safe:animate-[fade-up_600ms_ease-out_forwards]")}>{children}</p>;
}
