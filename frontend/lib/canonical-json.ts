function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function sortDeep(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(sortDeep);
  }
  if (isPlainObject(value)) {
    const keys = Object.keys(value).sort();
    const out: Record<string, unknown> = {};
    for (const key of keys) {
      out[key] = sortDeep(value[key]);
    }
    return out;
  }
  return value;
}

/** UTF-8 JSON with sorted object keys at every level, compact separators. */
export function canonicalJson(value: unknown): string {
  return JSON.stringify(sortDeep(value));
}
