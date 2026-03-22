import { describe, expect, it } from "vitest";

import type { DqcrAutocompleteData } from "./dqcrLanguage";
import { extractCteDefinitions, resolveAutocompleteContext } from "./dqcrLanguage";

function withCursor(input: string): { sql: string; offset: number } {
  const offset = input.indexOf("|");
  if (offset < 0) {
    throw new Error("Cursor marker '|' is required in test SQL.");
  }
  return {
    sql: input.slice(0, offset) + input.slice(offset + 1),
    offset,
  };
}

const baseData: DqcrAutocompleteData = {
  parameters: [],
  macros: [],
  configKeys: [],
  activeModelId: "SalesReport",
  objects: [
    {
      name: "dm.sales_report",
      kind: "target_table",
      source: "project_workflow",
      model_id: "SalesReport",
      path: "model/SalesReport/model.yml",
      lookup_keys: ["dm.sales_report", "sales_report"],
      columns: [
        { name: "id", domain_type: "number", is_key: true },
        { name: "amount", domain_type: "number", is_key: false },
      ],
    },
    {
      name: "Account",
      kind: "catalog_entity",
      source: "catalog",
      model_id: null,
      path: null,
      lookup_keys: ["Account"],
      columns: [
        { name: "ID", domain_type: "bigint", is_key: true },
        { name: "BranchID", domain_type: "decimal(19,0)", is_key: false },
      ],
    },
    {
      name: "_w.01_stage.001_main",
      kind: "workflow_query",
      source: "project_workflow",
      model_id: "SalesReport",
      path: "model/SalesReport/workflow/01_stage/001_main.sql",
      lookup_keys: ["_w.01_stage.001_main"],
      columns: [
        { name: "id", domain_type: "number", is_key: true },
        { name: "amount", domain_type: "number", is_key: false },
      ],
    },
  ],
};

describe("dqcrLanguage SQL autocomplete helpers", () => {
  it("extracts CTE names and projected columns", () => {
    const ctes = extractCteDefinitions(`
      with src as (
        select order_id as id, total_amount as amount
        from dm.orders
      )
      select *
      from src
    `);

    expect(ctes).toHaveLength(1);
    expect(ctes[0]?.name).toBe("src");
    expect(ctes[0]?.columns.map((item) => item.name)).toEqual(["id", "amount"]);
  });

  it("suggests local CTEs in object context before project objects", () => {
    const { sql, offset } = withCursor(`
      with src as (
        select order_id as id
        from dm.orders
      )
      select *
      from |
    `);

    const result = resolveAutocompleteContext(sql, offset, baseData);

    expect(result.mode).toBe("object");
    expect(result.objectSuggestions.map((item) => item.name).slice(0, 2)).toEqual(["src", "_w.01_stage.001_main"]);
  });

  it("resolves local CTE columns for alias member completion", () => {
    const { sql, offset } = withCursor(`
      with src as (
        select order_id as id, total_amount as amount
        from dm.orders
      )
      select s.|
      from src s
    `);

    const result = resolveAutocompleteContext(sql, offset, baseData);

    expect(result.mode).toBe("member");
    expect(result.columnSuggestions.map((item) => item.name)).toEqual(["id", "amount"]);
  });

  it("resolves project object columns for alias member completion", () => {
    const { sql, offset } = withCursor(`
      select t.|
      from dm.sales_report t
    `);

    const result = resolveAutocompleteContext(sql, offset, baseData);

    expect(result.mode).toBe("member");
    expect(result.columnSuggestions.map((item) => item.name)).toEqual(["id", "amount"]);
  });

  it("includes catalog entities in object-context suggestions", () => {
    const { sql, offset } = withCursor(`
      select *
      from |
    `);

    const result = resolveAutocompleteContext(sql, offset, baseData);

    expect(result.mode).toBe("object");
    expect(result.objectSuggestions.some((item) => item.name === "Account")).toBe(true);
  });

  it("resolves catalog entity columns for alias member completion", () => {
    const { sql, offset } = withCursor(`
      select a.|
      from Account a
    `);

    const result = resolveAutocompleteContext(sql, offset, baseData);

    expect(result.mode).toBe("member");
    expect(result.columnSuggestions.map((item) => item.name)).toEqual(["ID", "BranchID"]);
  });
});
