export function FeatureList({ items }: { items: { id: string; body: string }[] }) {
  return items.map((item, i) => (
    <div key={item.id} className="opacity-0 animate-in fade-in slide-in-from-bottom-4 fill-mode-forwards"
         style={{ animationDelay: `${i * 60}ms` }}>
      {item.body}
    </div>
  ));
}
