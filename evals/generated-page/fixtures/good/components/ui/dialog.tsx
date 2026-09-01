// Vendored by the shadcn / Base UI CLI. Nothing here was written by the
// generation, and every line below tripped a check on its first field run:
// `bg-black/10` is a scrim, and `h-(--positioner-height)` sits next to the word
// `animate` without anything being animated. Both must stay silent.
export function DialogBackdrop() {
  return <div className="fixed inset-0 z-50 bg-black/10 transition-opacity duration-150 data-ending-style:opacity-0" />;
}
export function DialogPopup() {
  return <div className="isolate z-50 h-(--positioner-height) w-(--positioner-width) data-open:animate-in" />;
}
