# Toolkit reference — TanStack Form + Zod backend

The 7 files of `lib/forms/` when `meta.json#stack.forms = "tanstack-form"`.

Dependencies:
- `@tanstack/react-form` ^1
- `zod` ^4
- shadcn `Field` component installed
- `sonner` mounted at the root layout

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

A thin React context wrapping the TanStack form instance so descendant `<FormField>` components can reach it without prop-drilling.

```tsx
"use client";
import { createContext, useContext, type ReactNode } from "react";
import type { AnyFormApi } from "@tanstack/react-form";

const FormContext = createContext<AnyFormApi | null>(null);

export function FormProvider({
  form,
  children,
}: {
  form: AnyFormApi;
  children: ReactNode;
}) {
  return <FormContext.Provider value={form}>{children}</FormContext.Provider>;
}

export function useFormContext(): AnyFormApi {
  const ctx = useContext(FormContext);
  if (!ctx) throw new Error("useFormContext must be used inside <FormProvider>");
  return ctx;
}
```

---

## `lib/forms/useEditForm.ts`

Manual-save hook with dirty tracking + baseline reset on success. The `save` callback **must throw on failure**; errors flow through `mapFormError`.

```ts
"use client";
import { useForm, type AnyFormApi } from "@tanstack/react-form";
import type { ZodTypeAny } from "zod/v4";
import { mapFormError } from "./mapFormError";

export interface UseEditFormOptions<T> {
  schema: ZodTypeAny;
  defaultValues: T;
  save: (value: T, ctx: { signal: AbortSignal }) => Promise<T>;
}

export function useEditForm<T>(opts: UseEditFormOptions<T>): AnyFormApi {
  let inFlight: AbortController | null = null;

  const form = useForm({
    defaultValues: opts.defaultValues as object,
    validators: {
      onChange: opts.schema as never,
      onBlur: opts.schema as never,
    },
    onSubmit: async ({ value }) => {
      inFlight?.abort();
      inFlight = new AbortController();
      try {
        const saved = await opts.save(value as T, { signal: inFlight.signal });
        // Reset baseline so isDirty returns to false; editing back to saved
        // value leaves the form clean.
        form.reset(saved as never);
      } catch (err) {
        mapFormError(err, { form });
        throw err; // re-throw so TanStack marks submit as failed
      } finally {
        inFlight = null;
      }
    },
  });

  return form as AnyFormApi;
}
```

---

## `lib/forms/useCreateForm.ts`

Same shape, no baseline reset; on success calls `onSuccess(result)`.

```ts
"use client";
import { useForm, type AnyFormApi } from "@tanstack/react-form";
import type { ZodTypeAny } from "zod/v4";
import { mapFormError } from "./mapFormError";

export interface UseCreateFormOptions<TInput, TResult> {
  schema: ZodTypeAny;
  defaultValues: TInput;
  submit: (value: TInput, ctx: { signal: AbortSignal }) => Promise<TResult>;
  onSuccess?: (result: TResult) => void;
}

export function useCreateForm<TInput, TResult>(
  opts: UseCreateFormOptions<TInput, TResult>,
): AnyFormApi {
  let inFlight: AbortController | null = null;

  const form = useForm({
    defaultValues: opts.defaultValues as object,
    validators: {
      onChange: opts.schema as never,
      onBlur: opts.schema as never,
    },
    onSubmit: async ({ value }) => {
      inFlight?.abort();
      inFlight = new AbortController();
      try {
        const result = await opts.submit(value as TInput, {
          signal: inFlight.signal,
        });
        opts.onSuccess?.(result);
      } catch (err) {
        mapFormError(err, { form });
        throw err;
      } finally {
        inFlight = null;
      }
    },
  });

  return form as AnyFormApi;
}
```

---

## `lib/forms/FormField.tsx`

Thin render-prop over `<form.Field name>` + shadcn `Field`/`FieldLabel`/`FieldError`. The child receives the TanStack field API.

```tsx
"use client";
import { type ReactNode } from "react";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field";
import { useFormContext } from "./FormProvider";

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
  }) => ReactNode;
}) {
  const form = useFormContext();
  return (
    <form.Field name={name}>
      {(field: never) => {
        // TanStack field API
        const f = field as {
          name: string;
          state: {
            value: unknown;
            meta: { isTouched: boolean; isValid: boolean; errors: unknown[] };
          };
          handleChange: (v: unknown) => void;
          handleBlur: () => void;
        };
        return (
          <Field
            data-invalid={f.state.meta.isTouched && !f.state.meta.isValid}
          >
            <FieldLabel htmlFor={name}>{label}</FieldLabel>
            {children({
              name: f.name,
              value: f.state.value,
              setValue: f.handleChange,
              onBlur: f.handleBlur,
              touched: f.state.meta.isTouched,
              isValid: f.state.meta.isValid,
              errors: f.state.meta.errors.map(String),
            })}
            {description && <FieldDescription>{description}</FieldDescription>}
            {f.state.meta.isTouched && !f.state.meta.isValid && (
              <FieldError>{String(f.state.meta.errors[0] ?? "")}</FieldError>
            )}
          </Field>
        );
      }}
    </form.Field>
  );
}
```

---

## `lib/forms/FormActions.tsx`

Save + Reset button row. Reads form state via `form.Subscribe` so only this subtree re-renders on state changes.

```tsx
"use client";
import { Button } from "@/components/ui/button";
import { useFormContext } from "./FormProvider";

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
  return (
    <form.Subscribe
      selector={(s: {
        canSubmit: boolean;
        isSubmitting: boolean;
        isDirty: boolean;
      }) => ({
        canSubmit: s.canSubmit,
        isSubmitting: s.isSubmitting,
        isDirty: s.isDirty,
      })}
    >
      {({
        canSubmit,
        isSubmitting,
        isDirty,
      }: {
        canSubmit: boolean;
        isSubmitting: boolean;
        isDirty: boolean;
      }) => (
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
            disabled={!canSubmit || (requireDirty && !isDirty)}
          >
            {isSubmitting ? submittingLabel : submitLabel}
          </Button>
        </div>
      )}
    </form.Subscribe>
  );
}
```

---

## `lib/forms/mapFormError.ts`

Discriminated-union routing for thrown errors. Extend `switch` cases as the project's error classes evolve. **Single source of truth** for form-level error UI.

```ts
"use client";
import { toast } from "sonner";
import type { AnyFormApi } from "@tanstack/react-form";

export interface FormErrorContext {
  form: AnyFormApi;
}

// Project-specific error classes (edit to match your services layer)
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
    // Redirect to your auth-refresh route — project-specific.
    window.location.assign("/auth/refresh");
    return;
  }
  if (err instanceof ForbiddenError) {
    toast.error("You don't have permission to perform this action.");
    return;
  }
  if (err instanceof ValidationProblem) {
    // Per-field errors — populate field meta.
    for (const [field, msgs] of Object.entries(err.errors)) {
      ctx.form.setFieldMeta(field as never, (m: never) => ({
        ...(m as object),
        errorMap: { onServer: msgs[0] },
      }) as never);
    }
    toast.error("Some fields need attention.");
    return;
  }
  if (err instanceof ServerProblem) {
    toast.error(err.detail);
    return;
  }
  if (err instanceof TypeError) {
    // Network failure
    toast.error("Network error. Please retry.");
    return;
  }
  toast.error("Something went wrong.");
}
```

---

## Notes

- **Adapt error classes** to your services layer. The `mapFormError` switch is the single source of truth — every form behaves identically because every form routes through it.
- **The form state stays dirty on error** so the user can fix and retry without losing edits.
- **`requireDirty` defaults to true** on `<FormActions>` for edit forms; pass `requireDirty={false}` for create forms (or split the component if your team prefers).
- **AbortController** is wired inside the hooks so re-submitting cancels the in-flight request. The button being disabled during submit is the primary defense; AbortController is the backstop for out-of-order resolution after reset.
- **i18n**: replace inline strings (`"Network error. Please retry."` etc.) with your i18n keys. The skill ships them inline; project should swap to `t("forms.errors.network")` etc.
