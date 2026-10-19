// A growing shadow on hover repaints the card every frame (rule 7): fade a layer that carries it instead.
export function HoverCard({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl transition-shadow hover:shadow-lg">{children}</div>;
}
