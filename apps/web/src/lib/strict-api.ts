/**
 * When true, the UI does not auto-switch to demo data if the API is unreachable
 * (avoids masking broken integrations during evaluation).
 */
export function isStrictApiMode(): boolean {
  return process.env.NEXT_PUBLIC_STRICT_API === "true";
}
