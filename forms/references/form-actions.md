# `<FormActions>` — custom layouts

The default `<FormActions submitLabel="Save" submittingLabel="Saving…" resetLabel="Reset" />` ships Save + Reset right-aligned. For non-trivial layouts (Cancel button, dialog footer docking, three-button row), drop `<FormActions>` and inline the equivalent subscribe block.

## TanStack Form — inline subscribe

```tsx
<form.Subscribe
  // Not `s.canSubmit`: TanStack's own flag folds in validity, which is not a gate here.
  selector={(s) => ({ isSubmitting: s.isSubmitting, isDirty: s.isDirty })}
>
  {({ isSubmitting, isDirty }) => (
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
        <Button type="submit" disabled={!isDirty || isSubmitting}>
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  )}
</form.Subscribe>
```

## react-hook-form — `useFormState`

```tsx
// `isValid` is deliberately absent: it is not a gate. See the skill, §The Save button is
// not a validity light.
const { isDirty, isSubmitting } = useFormState({ control: form.control });
const canSave = isDirty && !isSubmitting;

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
      <Button type="submit" disabled={!canSave}>
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
  <Button type="submit" disabled={!canSave}>
    {isSubmitting ? "Saving…" : "Save"}
  </Button>
</DialogFooter>
```

If `isDirty === true` when the user clicks Cancel, run the unsaved-changes guard (see `SKILL.md` § "Unsaved-changes guard") before closing.

## Three-button row (Save / Save and close / Cancel)

Common in admin tools:

```tsx
<form.Subscribe selector={(s) => ({ isDirty: s.isDirty, isSubmitting: s.isSubmitting })}>
  {({ isDirty, isSubmitting }) => (
    <div className="flex justify-end gap-2">
      <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
      <Button
        type="submit"
        variant="outline"
        disabled={!isDirty || isSubmitting}
        onClick={() => { /* set a flag the onSubmit reads */ }}
      >
        Save and close
      </Button>
      <Button type="submit" disabled={!isDirty || isSubmitting}>
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
- Not a place for confirmation modals. "Are you sure?" UX is the parent's concern; `<FormActions>` only disables while there is nothing to save or a save is in flight.
- 🔴 **Not a validity light.** Whatever layout you inline, the submit button must stay **enabled on an invalid form** — pressing it is the only thing that tells a screen-reader user which field is wrong. Any `disabled={!isValid}` you write here deletes that, and the error never reaches them. See the skill, §The Save button is not a validity light.

## Rule of thumb

Use `<FormActions>` when the layout is Save + Reset right-aligned. For anything else, drop to the subscribe block and own the layout. The skill flags the boundary but doesn't enforce the wrapper — the contract is the underlying form state discipline, not the button row.
