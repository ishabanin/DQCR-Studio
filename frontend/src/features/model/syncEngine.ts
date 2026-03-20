import Ajv from "ajv";
import YAML from "yaml";

import type { ModelObjectResponse } from "../../api/projects";

const ajv = new Ajv({ allErrors: true, strict: false });

function normalizeModel(input: unknown): ModelObjectResponse["model"] {
  const source = (input ?? {}) as Partial<ModelObjectResponse["model"]>;
  const target = (source.target_table ?? {}) as NonNullable<ModelObjectResponse["model"]["target_table"]>;
  const workflow = (source.workflow ?? {}) as NonNullable<ModelObjectResponse["model"]["workflow"]>;
  const cte = (source.cte_settings ?? {}) as NonNullable<ModelObjectResponse["model"]["cte_settings"]>;

  return {
    target_table: {
      name: target.name ?? "",
      schema: target.schema ?? "",
      description: target.description ?? "",
      template: target.template ?? "",
      engine: target.engine ?? "",
      attributes: Array.isArray(target.attributes) ? target.attributes : [],
    },
    workflow: {
      description: workflow.description ?? "",
      folders: Array.isArray(workflow.folders) ? workflow.folders : [],
    },
    cte_settings: {
      default: cte.default ?? "",
      by_context: typeof cte.by_context === "object" && cte.by_context ? cte.by_context : {},
    },
  };
}

export function formToYaml(model: ModelObjectResponse["model"]): string {
  return YAML.stringify(model).trimEnd() + "\n";
}

export function yamlToForm(
  yamlText: string,
  schema: Record<string, unknown> | null,
): { ok: true; model: ModelObjectResponse["model"] } | { ok: false; error: string } {
  try {
    const parsed = YAML.parse(yamlText) as unknown;
    if (schema) {
      const validate = ajv.compile(schema);
      const valid = validate(parsed);
      if (!valid) {
        const message = validate.errors?.[0]?.message ?? "YAML validation failed";
        return { ok: false, error: message };
      }
    }
    return { ok: true, model: normalizeModel(parsed) };
  } catch (error) {
    const message = error instanceof Error ? error.message : "YAML parse error";
    return { ok: false, error: message };
  }
}
