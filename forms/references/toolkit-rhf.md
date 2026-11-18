# Toolkit reference — react-hook-form + Zod backend

The 7 files of `lib/forms/` when `meta.json#stack.forms = "react-hook-form"`. The **consumer-facing API is identical** to the TanStack backend — same hook names, same `<FormProvider>` / `<FormField>` / `<FormActions>` / `mapFormError`. Only the implementation differs.

Dependencies:
- `react-hook-form` ^7
- `@hookform/resolvers` ^5
- `zod` ^4
- shadcn `Field` component installed
- a toast primitive mounted at the root layout — Base UI `Toast` (`components/ui/toast.tsx`)
  or `sonner`; `scaffold_lib_forms.py` rewrites the two `// forms:toast-*` lines of
  `mapFormError.ts` to match the one installed (see `toolkit-tanstack.md`).

---

## `lib/forms/index.ts`

```ts
export { useEditForm } from "./useEditForm";
export { useCreateForm } from "./useCreateForm";
export { FormProvider, useFormContext } from "./FormProvider";
export { FormField } from "./FormField";
export { FormActions } from "./FormActions";
export { mapFormError, type FormErrorContext } from "./mapFormError";
```

---

## `lib/forms/FormProvider.tsx`

Wraps RHF's `FormProvider` from `react-hook-form` (it already ships one) but with our context shape so the consumer signature stays identical to the TanStack version.

```tsx
"use client";
import {
  FormProvider as RHFProvider,
  useFormContext as useRHFFormContext,
  type UseFormReturn,
} from "react-hook-form";
import { type ReactNode } from "react";

export function FormProvider({
  form,
  children,
}: {
  form: UseFormReturn<never>;
  children: ReactNode;
}) {
  return <RHFProvider {...form}>{children}</RHFProvider>;
}

export function useFormContext(): UseFormReturn<never> {
  return useRHFFormContext<never>();
}
```

---

## `lib/forms/useEditForm.ts`

Manual-save hook with dirty tracking + baseline reset. RHF tracks dirty out of the box via `formState.isDirty`; the baseline reset uses RHF's `reset(value, { keepDirty: false })`.

```ts
"use client";
import { useRef } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { z } from "zod";
import { announce } from "@/lib/a11y/announcer";
import { mapFormError } from "./mapFormError";

export interface UseEditFormOptions<T> {
  schema: z.ZodType;
  defaultValues: T;
  save: (value: T, ctx: { signal: AbortSignal }) => Promise<T>;
}

export function useEditForm<T>(opts: UseEditFormOptions<T>): UseFormReturn<T> {
  const inFlightRef = useRef<AbortController | null>(null);

  const form = useForm<T>({
    defaultValues: opts.defaultValues as never,
    resolver: zodResolver(opts.schema),
    mode: "onChange", // validate on change so isValid is reactive
  });

  // Wrap handleSubmit so consumers can call `form.handleSubmit()` directly
  // and the save side-effects flow through mapFormError.
  const originalHandleSubmit = form.handleSubmit;
  form.handleSubmit = ((onValid?: never, onInvalid?: never) =>
    originalHandleSubmit(
      async (value: T) => {
        inFlightRef.current?.abort();
        inFlightRef.current = new AbortController();
        try {
          const saved = await opts.save(value, {
            signal: inFlightRef.current.signal,
          });
          form.reset(saved as never, { keepDirty: false, keepValues: true });
        } catch (err) {
          mapFormError(err, { form });
          throw err;
        } finally {
          inFlightRef.current = null;
        }
        onValid?.(value as never);
      },
      (errors) => {
        // RHF's `shouldFocusError` (on by default) already moved focus to the first errored
        // field, which announces that field's own message through `aria-describedby`. The
        // count is the part focus cannot say, so it is the only part the region says.
        const count = Object.keys(errors).length;
        if (count > 1) announce(`${count} fields need attention`);
        (onInvalid as ((e: typeof errors) => void) | undefined)?.(errors);
      },
    )) as never;

  return form;
}
```

---

## `lib/forms/useCreateForm.ts`

Same shape, no baseline reset; on success calls `onSuccess(result)`.

```ts
"use client";
import { useRef } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import type { z } from "zod";
import { announce } from "@/lib/a11y/announcer";
import { mapFormError } from "./mapFormError";

export interface UseCreateFormOptions<TInput, TResult> {
  schema: z.ZodType;
  defaultValues: TInput;
  submit: (value: TInput, ctx: { signal: AbortSignal }) => Promise<TResult>;
  onSuccess?: (result: TResult) => void;
}

export function useCreateForm<TInput, TResult>(
  opts: UseCreateFormOptions<TInput, TResult>,
): UseFormReturn<TInput> {
  const inFlightRef = useRef<AbortController | null>(null);

  const form = useForm<TInput>({
    defaultValues: opts.defaultValues as never,
    resolver: zodResolver(opts.schema),
    mode: "onChange",
  });

  const originalHandleSubmit = form.handleSubmit;
  form.handleSubmit = ((onValid?: never, onInvalid?: never) =>
    originalHandleSubmit(
      async (value: TInput) => {
        inFlightRef.current?.abort();
        inFlightRef.current = new AbortController();
        try {
          const result = await opts.submit(value, {
            signal: inFlightRef.current.signal,
          });
          opts.onSuccess?.(result);
        } catch (err) {
          mapFormError(err, { form });
          throw err;
        } finally {
          inFlightRef.current = null;
        }
        onValid?.(value as never);
      },
      (errors) => {
        // RHF's `shouldFocusError` (on by default) already moved focus to the first errored
        // field, which announces that field's own message through `aria-describedby`. The
        // count is the part focus cannot say, so it is the only part the region says.
        const count = Object.keys(errors).length;
        if (count > 1) announce(`${count} fields need attention`);
        (onInvalid as ((e: typeof errors) => void) | undefined)?.(errors);
      },
    )) as never;

  return form;
}
```

⚠️ **This is the one place the two toolkits are not symmetric, and it is in our favour.** RHF focuses
the first errored field itself (`shouldFocusError`, default `true`) — do not turn it off, and do not
add a second focus call on top of it. TanStack has no equivalent, which is why its side ships
`focusFirstInvalid()`. If a project sets `shouldFocusError: false`, that function is the replacement.

---

## `lib/forms/FormField.tsx`

Render-prop bridge over RHF's `Controller`, exposing the same shape as the TanStack `FormField` so consumer code stays identical.

```tsx
"use client";
import { type ReactNode } from "react";
import { Controller, useFormContext, useFormState } from "react-hook-form";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";

export function FormField({
  name,
  label,
  description,
  children,
}: {
  name: string;
  label: string;
  description?: string;
  children: (field: {
    name: string;
    value: unknown;
    setValue: (v: unknown) => void;
    onBlur: () => void;
    touched: boolean;
    isValid: boolean;
    errors: string[];
    /** Spread onto the control as `aria-invalid`. Mirrors `:user-invalid`. */
    invalid: boolean;
    /** Spread onto the control as `aria-describedby`; `undefined` while valid. */
    describedBy: string | undefined;
  }) => ReactNode;
}) {
  const { control } = useFormContext();
  // Reactive, and form-wide: one submit attempt flips every field to invalid at once,
  // which is what the failed-submit announcement needs.
  const { submitCount } = useFormState({ control });
  const errorId = `${name}-error`;
  return (
    <Controller
      control={control as never}
      name={name as never}
      render={({ field, fieldState }) => {
        // `:user-invalid`, not `:invalid`: modified and left, or a submit was attempted.
        // `isTouched` alone is blur — it reports an error on a field tabbed straight through.
        const invalid =
          ((fieldState.isDirty && fieldState.isTouched) || submitCount > 0) &&
          !!fieldState.error;
        const shown = invalid && Boolean(fieldState.error?.message);
        return (
          <Field data-invalid={invalid}>
            <FieldLabel htmlFor={name}>{label}</FieldLabel>
            {children({
              name: field.name,
              value: field.value,
              setValue: field.onChange,
              onBlur: field.onBlur,
              touched: fieldState.isTouched,
              invalid,
              // Only while shown: `<FieldError>` is unmounted otherwise, and a permanent
              // reference is announced before the user has touched the field.
              describedBy: shown ? errorId : undefined,
              isValid: !fieldState.error,
              errors: fieldState.error?.message ? [fieldState.error.message] : [],
            })}
            {description && <FieldDescription>{description}</FieldDescription>}
            {shown && <FieldError id={errorId}>{fieldState.error?.message}</FieldError>}
          </Field>
        );
      }}
    />
  );
}
```

---

## `lib/forms/FormActions.tsx`

Save + Reset row. RHF re-renders on `formState` changes; we use `useFormState` (the targeted subscription primitive) to avoid re-rendering on unrelated fields.

```tsx
"use client";
import { useFormState, useFormContext } from "react-hook-form";
import { Button } from "@/components/ui/button";

export function FormActions({
  submitLabel,
  submittingLabel,
  resetLabel = "Reset",
  requireDirty = true,
}: {
  submitLabel: string;
  submittingLabel: string;
  resetLabel?: string;
  requireDirty?: boolean;
}) {
  const form = useFormContext();
  // `isValid` is deliberately not read here: it is not a gate. See the `forms` skill,
  // §The Save button is not a validity light.
  const { isDirty, isSubmitting } = useFormState({ control: form.control });
  return (
    <div className="flex justify-end gap-2">
      <Button
        type="button"
        variant="ghost"
        disabled={!isDirty || isSubmitting}
        onClick={() => form.reset()}
      >
        {resetLabel}
      </Button>
      <Button
        type="submit"
        // Nothing to save, or a save in flight. An invalid form keeps an enabled button:
        // pressing it is how the user is told what is wrong.
        disabled={isSubmitting || (requireDirty && !isDirty)}
      >
        {isSubmitting ? submittingLabel : submitLabel}
      </Button>
    </div>
  );
}
```

---

## `lib/forms/mapFormError.ts`

Identical surface to the TanStack version; only the per-field setter changes — RHF uses `setError`.

```ts
"use client";
import type { UseFormReturn } from "react-hook-form";
import { toast } from "@/components/ui/toast"; // forms:toast-import

export interface FormErrorContext {
  form: UseFormReturn<never>;
}

function notifyError(message: string): void {
  toast.add({ title: message, type: "error" }); // forms:toast-call
}

class SessionExpiredError extends Error {}
class ForbiddenError extends Error {}
class ValidationProblem extends Error {
  errors: Record<string, string[]>;
  constructor(errors: Record<string, string[]>) {
    super("validation");
    this.errors = errors;
  }
}
class ServerProblem extends Error {
  detail: string;
  constructor(detail: string) {
    super(detail);
    this.detail = detail;
  }
}

export function mapFormError(err: unknown, ctx: FormErrorContext): void {
  if (err instanceof SessionExpiredError) {
    // A full reload on purpose: it drops client state tied to the dead session.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/auth/refresh");
    return;
  }
  if (err instanceof ForbiddenError) {
    notifyError("You don't have permission to perform this action.");
    return;
  }
  if (err instanceof ValidationProblem) {
    for (const [field, msgs] of Object.entries(err.errors)) {
      ctx.form.setError(field as never, {
        type: "server",
        message: msgs[0],
      });
    }
    notifyError("Some fields need attention.");
    return;
  }
  if (err instanceof ServerProblem) {
    notifyError(err.detail);
    return;
  }
  if (err instanceof TypeError) {
    notifyError("Network error. Please retry.");
    return;
  }
  notifyError("Something went wrong.");
}
```

---

## Notes — TanStack vs RHF differences (internal only)

| Concern | TanStack Form | react-hook-form |
|---|---|---|
| Dirty tracking | `state.isDirty` (deep equal) | `formState.isDirty` (RHF tracks per field) |
| Baseline reset | `form.reset(savedValue)` | `form.reset(saved, { keepDirty: false })` |
| Per-field error from server | `setFieldMeta` + `errorMap.onServer` | `setError(field, { type: "server", message })` |
| Subscribe primitive | `form.Subscribe selector={...}` | `useFormState({ control })` |
| Field render prop | `<form.Field name>` | `<Controller name render={({field, fieldState})}>` |
| Validation trigger | Pass schema to `validators: {onChange, onBlur}` | `zodResolver(schema)` + `mode: "onChange"` |

Consumer code (the components that import `useEditForm` / `useCreateForm` / `FormField` / `FormActions`) is **identical** across both backends. That's the contract.
