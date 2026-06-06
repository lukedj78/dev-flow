# `<FormActions>` — custom layouts

The default `<FormActions submitLabel="Save" submittingLabel="Saving…" resetLabel="Reset" />` ships Save + Reset right-aligned. For non-trivial layouts (Cancel button, dialog footer docking, three-button row), drop `<FormActions>` and inline the equivalent subscribe block.

## TanStack Form — inline subscribe

```tsx
<form.Subscribe
  selector={(s) => ({
    canSubmit: s.canSubmit,
    isSubmitting: s.isSubmitting,
    isDirty: s.isDirty,
  })}
>
  {({ canSubmit, isSubmitting, isDirty }) => (
    <div className="flex items-center justify-between gap-2">
      <Button type="button" variant="ghost" onClick={onCancel}>
        Cancel
      </Button>
      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={!isDirty || isSubmitting}
          onClick={() => form.reset()}
        >
          Reset
        </Button>
        <Button type="submit" disabled={!canSubmit}>
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  )}
</form.Subscribe>
```

## react-hook-form — `useFormState`

```tsx
const { isDirty, isValid, isSubmitting } = useFormState({ control: form.control });
const canSubmit = isValid && !isSubmitting;

return (
  <div className="flex items-center justify-between gap-2">
    <Button type="button" variant="ghost" onClick={onCancel}>
      Cancel
    </Button>
    <div className="flex gap-2">
      <Button
        type="button"
        variant="outline"
        disabled={!isDirty || isSubmitting}
        onClick={() => form.reset()}
      >
        Reset
      </Button>
      <Button type="submit" disabled={!canSubmit}>
        {isSubmitting ? "Saving…" : "Save"}
      </Button>
    </div>
  </div>
);
```

## Dialog footer pattern

When the form lives inside a shadcn `<Dialog>`, the natural place for actions is `<DialogFooter>`:

```tsx
<DialogFooter>
  <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
    Cancel
  </Button>
  <Button type="submit" disabled={!canSubmit}>
    {isSubmitting ? "Saving…" : "Save"}
  </Button>
</DialogFooter>
```

If `isDirty === true` when the user clicks Cancel, run the unsaved-changes guard (see `SKILL.md` § "Unsaved-changes guard") before closing.

## Three-button row (Save / Save and close / Cancel)

Common in admin tools:

```tsx
<form.Subscribe selector={(s) => ({ canSubmit: s.canSubmit, isSubmitting: s.isSubmitting })}>
  {({ canSubmit, isSubmitting }) => (
    <div className="flex justify-end gap-2">
      <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
      <Button
        type="submit"
        variant="outline"
        disabled={!canSubmit}
        onClick={() => { /* set a flag the onSubmit reads */ }}
      >
        Save and close
      </Button>
      <Button type="submit" disabled={!canSubmit}>
        {isSubmitting ? "Saving…" : "Save"}
      </Button>
    </div>
  )}
</form.Subscribe>
```

To distinguish "Save" from "Save and close" inside the hook's `save` callback, pass a `useState`-controlled flag through React context, **or** prefer two separate handlers wired to two separate `<Button onClick>` handlers that each call `form.handleSubmit()` after setting the flag.

## What `<FormActions>` is NOT

- Not a Cancel button. Cancel is a parent concern (close the dialog, navigate away, etc.); the form has no opinion on it.
- Not a place for "Save and continue editing" auto-save. The skill bans auto-save — the contract is explicit Save click. If you genuinely need workflow buttons, inline the subscribe block and own the layout.
- Not a place for confirmation modals. "Are you sure?" UX is the parent's concern; `<FormActions>` only disables until `canSubmit && isDirty`.

## Rule of thumb

Use `<FormActions>` when the layout is Save + Reset right-aligned. For anything else, drop to the subscribe block and own the layout. The skill flags the boundary but doesn't enforce the wrapper — the contract is the underlying form state discipline, not the button row.
