/**
 * useZodForm — bridge between react-hook-form and Zod schemas.
 *
 * Wraps react-hook-form's useForm with zodResolver for type-safe
 * form handling across all modules.
 *
 * Checklist items: #309, #310, #446
 */

import { useForm, UseFormProps, UseFormReturn, FieldValues, Path } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCallback, useRef } from "react";

/**
 * Custom hook that wraps react-hook-form with Zod validation.
 *
 * @example
 * ```tsx
 * import { inspectionSchema, InspectionFormData } from "@/lib/schemas";
 *
 * function InspectionForm() {
 *   const form = useZodForm({
 *     schema: inspectionSchema,
 *     defaultValues: { title: "", type: "incoming", priority: "medium" },
 *   });
 *
 *   const onSubmit = form.handleSubmit(async (data) => {
 *     await createInspection(data);
 *   });
 *
 *   return (
 *     <form onSubmit={onSubmit}>
 *       <input {...form.register("title")} />
 *       {form.formState.errors.title && (
 *         <span>{form.formState.errors.title.message}</span>
 *       )}
 *     </form>
 *   );
 * }
 * ```
 */
export function useZodForm<TSchema extends z.ZodType<any, any, any>>(
  props: Omit<UseFormProps<z.infer<TSchema>>, "resolver"> & {
    schema: TSchema;
  }
): UseFormReturn<z.infer<TSchema>> {
  const { schema, ...formProps } = props;

  return useForm<z.infer<TSchema>>({
    ...formProps,
    resolver: zodResolver(schema),
    mode: formProps.mode ?? "onBlur",
  });
}

/**
 * Helper to get error message for a field.
 */
export function getFieldError<T extends FieldValues>(
  form: UseFormReturn<T>,
  field: Path<T>
): string | undefined {
  const error = form.formState.errors[field];
  return error?.message as string | undefined;
}

/**
 * Helper to check if a form field has been touched and has an error.
 */
export function hasFieldError<T extends FieldValues>(
  form: UseFormReturn<T>,
  field: Path<T>
): boolean {
  return (
    !!form.formState.errors[field] &&
    (form.formState.touchedFields[field] || form.formState.isSubmitted)
  );
}

export type { UseFormReturn } from "react-hook-form";
