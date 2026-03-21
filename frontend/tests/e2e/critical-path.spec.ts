import { expect, Page, test } from "@playwright/test";

const PROJECT_ID = "demo";
const MODEL_ID = "SampleModel";
const SQL_PATH = "model/SampleModel/workflow/01_stage/001_main.sql";

async function mockApi(page: Page): Promise<void> {
  let sqlContent = "-- comment\nSELECT 1 AS id\n";
  let createdProjectId = "new-project";

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/v1/projects" && method === "GET") {
      await route.fulfill({ json: [{ id: PROJECT_ID, name: "Demo Project" }, { id: createdProjectId, name: createdProjectId }] });
      return;
    }

    if (path === "/api/v1/projects" && method === "POST") {
      const payload = request.postDataJSON() as { project_id?: string };
      createdProjectId = payload.project_id ?? createdProjectId;
      await route.fulfill({ json: { id: createdProjectId, name: createdProjectId, contexts: ["default"], model: MODEL_ID } });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/contexts`) {
      await route.fulfill({ json: [{ id: "default", name: "default" }] });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/files/tree`) {
      await route.fulfill({
        json: {
          name: PROJECT_ID,
          path: ".",
          type: "directory",
          children: [
            {
              name: "model",
              path: "model",
              type: "directory",
              children: [
                {
                  name: MODEL_ID,
                  path: `model/${MODEL_ID}`,
                  type: "directory",
                  children: [
                    {
                      name: "workflow",
                      path: `model/${MODEL_ID}/workflow`,
                      type: "directory",
                      children: [
                        {
                          name: "01_stage",
                          path: `model/${MODEL_ID}/workflow/01_stage`,
                          type: "directory",
                          children: [
                            { name: "001_main.sql", path: SQL_PATH, type: "file" },
                            { name: "folder.yml", path: `model/${MODEL_ID}/workflow/01_stage/folder.yml`, type: "file" },
                          ],
                        },
                      ],
                    },
                    { name: "model.yml", path: `model/${MODEL_ID}/model.yml`, type: "file" },
                  ],
                },
              ],
            },
            { name: "project.yml", path: "project.yml", type: "file" },
          ],
        },
      });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/models/${MODEL_ID}/lineage`) {
      await route.fulfill({
        json: {
          project_id: PROJECT_ID,
          model_id: MODEL_ID,
          nodes: [
            {
              id: "01_stage",
              name: "01_stage",
              path: `model/${MODEL_ID}/workflow/01_stage`,
              materialized: "insert_fc",
              enabled_contexts: ["default"],
              queries: ["001_main.sql"],
              parameters: [],
              ctes: [],
            },
          ],
          edges: [],
          summary: { folders: 1, queries: 1, params: 0 },
        },
      });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/files/content` && method === "GET") {
      await route.fulfill({ json: { path: SQL_PATH, content: sqlContent } });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/files/content` && method === "PUT") {
      const payload = request.postDataJSON() as { content: string };
      sqlContent = payload.content;
      await route.fulfill({ json: { status: "saved", path: SQL_PATH } });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/autocomplete`) {
      await route.fulfill({ json: { parameters: [], macros: [], config_keys: [], objects: [] } });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/models/${MODEL_ID}/config-chain`) {
      await route.fulfill({
        json: {
          levels: [],
          resolved: [],
          cte_settings: { default: null, by_context: {} },
          generated_outputs: [],
        },
      });
      return;
    }

    if (path === `/api/v1/projects/schema/model-yml`) {
      await route.fulfill({ json: { type: "object" } });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/models/${MODEL_ID}` && method === "GET") {
      await route.fulfill({
        json: {
          project_id: PROJECT_ID,
          model_id: MODEL_ID,
          path: `model/${MODEL_ID}/model.yml`,
          model: {
            target_table: {
              name: "sample_table",
              schema: "dm",
              description: "sample",
              template: "dqcr",
              engine: "oracle",
              attributes: [{ name: "id", domain_type: "number", is_key: true }],
            },
            workflow: {
              description: "sample workflow",
              folders: [{ id: "01_stage", enabled: true, materialization: "insert_fc", pattern: "load" }],
            },
            cte_settings: { default: "insert_fc", by_context: {} },
          },
        },
      });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/validate` && method === "POST") {
      await route.fulfill({
        json: {
          run_id: "val-1",
          timestamp: new Date().toISOString(),
          project: PROJECT_ID,
          model: MODEL_ID,
          summary: { passed: 2, warnings: 0, errors: 0 },
          rules: [],
        },
      });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/validate/history`) {
      await route.fulfill({ json: [] });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/build` && method === "POST") {
      await route.fulfill({
        json: {
          build_id: "bld-1",
          timestamp: new Date().toISOString(),
          project: PROJECT_ID,
          model: MODEL_ID,
          engine: "dqcr",
          context: "default",
          dry_run: false,
          output_path: ".dqcr_builds/bld-1",
          files_count: 1,
          files: [{ path: `${MODEL_ID}/workflow/01_stage/001_main.sql`, source_path: SQL_PATH, size_bytes: 100 }],
        },
      });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/build/history`) {
      await route.fulfill({ json: [] });
      return;
    }

    await route.fulfill({ status: 200, json: {} });
  });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test("critical path: open project to lineage", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Lineage" })).toBeVisible();
  await expect(page.getByText("1 folders")).toBeVisible();
  await expect(page.getByRole("heading", { name: "01_stage" })).toBeVisible();
});

test("critical path: edit sql, save and validate", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "SQL Editor" }).click();
  await page.getByRole("button", { name: "001_main.sql" }).first().click();
  await page.keyboard.type("\nSELECT 2 AS id");
  await page.getByRole("button", { name: "Save (Ctrl+S)" }).click();
  await page.getByRole("banner").getByRole("button", { name: "Validate" }).click();
  await expect(page.getByText("Validate Screen")).toBeVisible();
});

test("critical path: wizard create and build", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New Project" }).click();
  await expect(page.getByText("Create Project")).toBeVisible();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Create Project" }).click();
  await page.evaluate(() => {
    const closeButton = Array.from(document.querySelectorAll("button")).find((el) => el.textContent?.trim() === "Close");
    closeButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
  await page.evaluate(() => {
    const buildButton = Array.from(document.querySelectorAll("button")).find((el) => el.textContent?.trim() === "Build");
    buildButton?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
  await expect(page.getByRole("heading", { name: "Build", exact: true })).toBeVisible();
});

test("model editor sync mode switches and keeps status", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Model Editor" }).click();
  await expect(page.getByRole("heading", { name: "Model Editor" })).toBeVisible();
  await expect(page.getByText("Sync:")).toBeVisible();
  await page.getByRole("button", { name: "YAML" }).click();
  await expect(page.getByText("Schema:")).toBeVisible();
  await page.getByRole("button", { name: "Visual" }).click();
  await expect(page.getByRole("heading", { name: "Target Table" })).toBeVisible();
});
