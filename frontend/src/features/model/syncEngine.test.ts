import { describe, expect, it } from "vitest";

import type { ModelObjectResponse } from "../../api/projects";
import { formToYaml, yamlToForm } from "./syncEngine";

const SAMPLE_MODEL: ModelObjectResponse["model"] = {
  target_table: {
    name: "sales_report",
    schema: "dm",
    description: "sales report",
    template: "dqcr",
    engine: "oracle",
    attributes: [{ name: "id", domain_type: "number", is_key: true }],
  },
  workflow: {
    description: "workflow",
    folders: [{ id: "01_stage", enabled: true, materialization: "insert_fc" }],
  },
  cte_settings: {
    default: "insert_fc",
    by_context: { dev: "insert_fc" },
  },
};

describe("syncEngine", () => {
  it("serializes model to yaml with trailing newline", () => {
    const result = formToYaml(SAMPLE_MODEL);
    expect(result).toContain("target_table:");
    expect(result.endsWith("\n")).toBe(true);
  });

  it("parses yaml and validates schema when provided", () => {
    const yaml = formToYaml(SAMPLE_MODEL);
    const schema = {
      type: "object",
      required: ["target_table", "workflow"],
    } as const;
    const parsed = yamlToForm(yaml, schema as unknown as Record<string, unknown>);
    expect(parsed.ok).toBe(true);
    if (parsed.ok) {
      expect(parsed.model.target_table.name).toBe("sales_report");
      expect(parsed.model.workflow.folders).toHaveLength(1);
    }
  });

  it("returns validation error when schema does not match", () => {
    const yaml = "target_table: {}\nworkflow: {}\n";
    const schema = {
      type: "object",
      required: ["missing"],
    } as const;
    const parsed = yamlToForm(yaml, schema as unknown as Record<string, unknown>);
    expect(parsed.ok).toBe(false);
    if (!parsed.ok) {
      expect(parsed.error.length).toBeGreaterThan(0);
    }
  });
});

