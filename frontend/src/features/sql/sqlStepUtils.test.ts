import { describe, expect, it } from "vitest";

import { getStepFolder, getStepMatchScore, getStepQueryName, parseSqlFileKey } from "./sqlStepUtils";

describe("sqlStepUtils", () => {
  it("parses SQL file path into folder and query name", () => {
    expect(parseSqlFileKey("model/RF110RestTurnReg/SQL/001_Load__distr/001_RF110_Reg_Acc2.sql")).toEqual({
      folder: "001_Load__distr",
      queryName: "001_RF110_Reg_Acc2",
    });
  });

  it("extracts step folder and query name from workflow step metadata", () => {
    const step = {
      folder: "001_Load__distr",
      name: "001_RF110_Reg_Acc2",
      step_type: "sql",
      full_name: "001_Load__distr/001_RF110_Reg_Acc2_default/sql",
      sql_model: {
        name: "001_RF110_Reg_Acc2",
        path: "/app/projects/rf110new/model/RF110RestTurnReg/SQL/001_Load__distr/001_RF110_Reg_Acc2.sql",
      },
    };

    expect(getStepFolder(step)).toBe("001_Load__distr");
    expect(getStepQueryName(step)).toBe("001_RF110_Reg_Acc2");
  });

  it("prefers the step for the active context when multiple matches exist", () => {
    const key = { folder: "001_Load__distr", queryName: "001_RF110_Reg_Acc2" };
    const activeStep = {
      folder: "001_Load__distr",
      step_type: "sql",
      context: "default",
      full_name: "001_Load__distr/001_RF110_Reg_Acc2_default/sql",
      sql_model: {
        name: "001_RF110_Reg_Acc2",
        path: "/app/projects/rf110new/model/RF110RestTurnReg/SQL/001_Load__distr/001_RF110_Reg_Acc2.sql",
      },
    };
    const fallbackStep = {
      folder: "001_Load__distr",
      step_type: "sql",
      context: "all",
      full_name: "001_Load__distr/001_RF110_Reg_Acc2_all/sql",
      sql_model: {
        name: "001_RF110_Reg_Acc2",
        path: "/app/projects/rf110new/model/RF110RestTurnReg/SQL/001_Load__distr/001_RF110_Reg_Acc2.sql",
      },
    };

    expect(getStepMatchScore(activeStep, key, "default")).toBeGreaterThan(getStepMatchScore(fallbackStep, key, "default"));
  });

  it("rejects unrelated SQL steps", () => {
    const key = { folder: "001_Load__distr", queryName: "001_RF110_Reg_Acc2" };
    const step = {
      folder: "002_Update",
      step_type: "sql",
      context: "default",
      full_name: "002_Update/001_RF110RestTurnReg_QUALITY_default/sql",
      sql_model: {
        name: "001_RF110RestTurnReg_QUALITY",
        path: "/app/projects/rf110new/model/RF110RestTurnReg/SQL/002_Update/001_RF110RestTurnReg_QUALITY.sql",
      },
    };

    expect(getStepMatchScore(step, key, "default")).toBe(-1);
  });
});
