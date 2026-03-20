import { describe, expect, it } from "vitest";

import type { ModelObjectResponse } from "../../api/projects";
import { areModelsEqual, normalizeYamlText, resolveYamlSyncStatus } from "./yamlSync";

const BASE_MODEL: ModelObjectResponse["model"] = {
  target_table: {
    name: "orders",
    schema: "dm",
    description: "",
    template: "dqcr",
    engine: "dbt",
    attributes: [],
  },
  workflow: { description: "", folders: [] },
  cte_settings: { default: "", by_context: {} },
};

describe("yamlSync utilities", () => {
  it("normalizes line breaks and enforces trailing newline", () => {
    expect(normalizeYamlText("a: 1\r\nb: 2")).toBe("a: 1\nb: 2\n");
  });

  it("compares models by value", () => {
    const copy = JSON.parse(JSON.stringify(BASE_MODEL)) as ModelObjectResponse["model"];
    expect(areModelsEqual(BASE_MODEL, copy)).toBe(true);
  });

  it("maps yaml parse result to sync status", () => {
    expect(resolveYamlSyncStatus(false)).toBe("synced");
    expect(resolveYamlSyncStatus(true)).toBe("conflict");
  });
});

