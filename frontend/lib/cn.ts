/** Joins truthy class names. Tiny on purpose: no extra dependency. */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
