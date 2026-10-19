// Rule 7's recipe: the final shadow lives on ::after and only its opacity animates.
export function HoverCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative rounded-xl after:pointer-events-none after:absolute after:inset-0 after:rounded-[inherit] after:shadow-lg after:opacity-0 after:transition-opacity hover:after:opacity-100 motion-reduce:after:transition-none">
      {children}
    </div>
  );
}
