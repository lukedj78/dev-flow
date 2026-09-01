"use client";
export default function Error({ reset }: { reset: () => void }) {
  return <button onClick={reset} className="active:scale-[0.98]">Try again</button>;
}
