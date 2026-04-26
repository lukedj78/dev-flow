"use client";

import * as React from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

/**
 * Theme switcher with a global keyboard shortcut: pressing the `D` key
 * anywhere on the page toggles between light and dark, except when the user
 * is typing in an input/textarea/contenteditable. This pattern is part of
 * the design-md-to-app site-shell — every project gets it for free.
 */
export function ModeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const toggle = React.useCallback(() => {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }, [resolvedTheme, setTheme]);

  React.useEffect(() => {
    function isTyping(target: EventTarget | null) {
      if (!(target instanceof HTMLElement)) return false;
      const tag = target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
      if (target.isContentEditable) return true;
      // Rich-text editors (Tiptap, ProseMirror, Slate) and component libraries
      // (Radix combobox) often render as <div role="textbox"> or carry a
      // [data-editor] / [data-slate-editor] hook. Catch those too — pressing D
      // inside a Notion-style editor flipping the theme is jarring.
      const role = target.getAttribute("role");
      if (role === "textbox" || role === "combobox" || role === "searchbox") return true;
      if (target.closest("[data-editor], [data-slate-editor], [contenteditable='true']")) return true;
      return false;
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== "d" && e.key !== "D") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTyping(e.target)) return;
      e.preventDefault();
      toggle();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toggle]);

  // Avoid SSR/CSR mismatch — render an inert placeholder until mounted.
  if (!mounted) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className="text-on-surface-variant"
        aria-label="Toggle theme"
      >
        <Sun className="size-4" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className="text-on-surface-variant"
      aria-label={`Toggle theme (current: ${resolvedTheme}). Shortcut: D`}
      title="Press D to toggle theme"
      onClick={toggle}
    >
      {resolvedTheme === "dark" ? (
        <Sun className="size-4" />
      ) : (
        <Moon className="size-4" />
      )}
    </Button>
  );
}
