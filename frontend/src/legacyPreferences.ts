const LEGACY_INTERFACE_PREFERENCE_KEYS = [
  "expertMode",
  "expert_mode",
  "simpleMode",
  "simple_mode",
  "odin.expertMode",
  "odin.expert_mode",
  "odin.simpleMode",
  "odin.simple_mode",
] as const;

export function removeLegacyInterfacePreferences(
  storage?: Pick<Storage, "removeItem">,
) {
  if (!storage) {
    try {
      storage = globalThis.localStorage;
    } catch {
      return;
    }
  }
  if (!storage) return;

  for (const key of LEGACY_INTERFACE_PREFERENCE_KEYS) {
    try {
      storage.removeItem(key);
    } catch {
      // Storage may be unavailable or blocked. Old preferences must never
      // prevent the complete interface from loading.
    }
  }
}
