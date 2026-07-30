import { describe, expect, it, vi } from "vitest";

import { removeLegacyInterfacePreferences } from "./legacyPreferences";

describe("legacy interface preferences", () => {
  it("removes old stored preferences without using their values", () => {
    const removeItem = vi.fn();

    removeLegacyInterfacePreferences({ removeItem });

    expect(removeItem).toHaveBeenCalledWith("expertMode");
    expect(removeItem).toHaveBeenCalledWith("simpleMode");
    expect(removeItem).toHaveBeenCalledWith("odin.expert_mode");
    expect(removeItem).toHaveBeenCalledWith("odin.simple_mode");
  });

  it("tolerates storage failures", () => {
    expect(() =>
      removeLegacyInterfacePreferences({
        removeItem: () => {
          throw new DOMException("blocked");
        },
      }),
    ).not.toThrow();
  });
});
