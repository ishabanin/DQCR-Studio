import { describe, expect, it } from "vitest";

import { buildValidationBadges } from "./useValidationBadges";

describe("buildValidationBadges", () => {
  it("propagates file issues to parent folders and respects error priority", () => {
    const badges = buildValidationBadges([
      {
        rule_id: "r1",
        name: "rule1",
        status: "warning",
        message: "warning issue",
        file_path: "model/Sample/workflow/01_stage/001_main.sql",
        line: 2,
      },
      {
        rule_id: "r2",
        name: "rule2",
        status: "error",
        message: "error issue",
        file_path: "model/Sample/workflow/01_stage/002_extra.sql",
        line: 3,
      },
      {
        rule_id: "r3",
        name: "rule3",
        status: "pass",
        message: "info issue",
        file_path: "model/Sample/workflow/02_stage/001_other.sql",
        line: 1,
      },
    ]);

    expect(badges.get("model/Sample/workflow/01_stage/001_main.sql")?.level).toBe("warning");
    expect(badges.get("model/Sample/workflow/01_stage/002_extra.sql")?.level).toBe("error");
    expect(badges.get("model/Sample/workflow/01_stage")?.level).toBe("error");
    expect(badges.get("model/Sample/workflow")?.level).toBe("error");
    expect(badges.get("model/Sample/workflow/02_stage")?.level).toBe("info");
    expect(badges.get("model/Sample")?.level).toBe("error");
  });
});
