import { expect, Page, test } from "@playwright/test";

const PROJECT_ID = "demo";
const MODEL_ID = "SampleModel";
const SQL_PATH = "model/SampleModel/workflow/01_stage/001_main.sql";

interface MockApiState {
  autocompleteObjectNames: string[];
  autocompleteRequestCount: number;
  modelSaveCount: number;
  catalogUploaded: boolean;
}

let currentMockState: MockApiState;

async function openProjectWorkspace(page: Page): Promise<void> {
  if ((await page.locator("nav.tabbar").count()) > 0) return;
  const firstProjectCard = page.locator(".hub-project-card").first();
  await expect(firstProjectCard).toBeVisible();
  await firstProjectCard.click();
  await expect(page.locator("nav.tabbar")).toBeVisible({ timeout: 10000 });
}

async function mockApi(page: Page): Promise<MockApiState> {
  let sqlContent = "-- comment\nSELECT 1 AS id\n";
  let createdProjectId = "new-project";
  let catalogUploaded = false;
  const catalogEntity = {
    name: "Account",
    display_name: "Account",
    module: "CRM",
    description: "Account entity",
    attributes: [
      {
        position: 1,
        name: "account_id",
        display_name: "Account ID",
        domain_type: "number",
        raw_type: "NUMBER",
        is_key: true,
        is_nullable: false,
      },
      {
        position: 2,
        name: "account_name",
        display_name: "Account name",
        domain_type: "string",
        raw_type: "VARCHAR2",
        is_key: false,
        is_nullable: false,
      },
    ],
  };

  let modelObject = {
    target_table: {
      name: "sample_table",
      table: "sample_table",
      schema: "dm",
      description: "sample",
      template: "dqcr",
      engine: "oracle",
      attributes: [{ name: "id", domain_type: "number", is_key: true }],
    },
    fields: [] as Array<{
      name: string;
      display_name?: string | null;
      type?: string | null;
      is_key?: boolean | null;
      nullable?: boolean | null;
    }>,
    workflow: {
      description: "sample workflow",
      folders: [{ id: "01_stage", enabled: true, materialization: "insert_fc", pattern: "load" }],
    },
    cte_settings: { default: "insert_fc", by_context: {} },
  };

  const state: MockApiState = {
    autocompleteObjectNames: [],
    autocompleteRequestCount: 0,
    modelSaveCount: 0,
    catalogUploaded: false,
  };

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/v1/projects" && method === "GET") {
      await route.fulfill({ json: [{ id: PROJECT_ID, name: "Demo Project" }, { id: createdProjectId, name: createdProjectId }] });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}` && method === "GET") {
      await route.fulfill({ json: { id: PROJECT_ID, name: "Demo Project" } });
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

    if (path === `/api/v1/projects/${PROJECT_ID}/parameters` && method === "GET") {
      await route.fulfill({ json: [] });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/workflow/status` && method === "GET") {
      await route.fulfill({
        json: {
          project_id: PROJECT_ID,
          overall: "ready",
          status: "ready",
          models: [{ model_id: MODEL_ID, status: "ready", source: "project_workflow" }],
        },
      });
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
      const requestedPath = url.searchParams.get("path") ?? SQL_PATH;
      if (requestedPath === "project.yml") {
        await route.fulfill({
          json: {
            path: requestedPath,
            content: "name: Demo Project\ndescription: demo\ntemplate: flx\nproperties:\n  version: v1\n  owner: test\n",
          },
        });
        return;
      }
      if (requestedPath === "contexts/default.yml") {
        await route.fulfill({
          json: {
            path: requestedPath,
            content: "tools: []\nconstants: {}\nflags:\n  default: true\n",
          },
        });
        return;
      }
      await route.fulfill({ json: { path: requestedPath, content: sqlContent } });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/files/content` && method === "PUT") {
      const payload = request.postDataJSON() as { content: string };
      sqlContent = payload.content;
      await route.fulfill({ json: { status: "saved", path: SQL_PATH } });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/autocomplete`) {
      state.autocompleteRequestCount += 1;
      const columns = (modelObject.fields ?? []).map((field) => ({
        name: field.name,
        domain_type: field.type ?? null,
        is_key: field.is_key ?? null,
      }));
      const objectName = modelObject.target_table.table ?? modelObject.target_table.name ?? "sample_table";
      const objects =
        columns.length > 0
          ? [
              {
                name: objectName,
                kind: "target_table",
                source: "project_model_fallback",
                model_id: MODEL_ID,
                path: `model/${MODEL_ID}/model.yml`,
                lookup_keys: [objectName.toLowerCase(), MODEL_ID.toLowerCase()],
                columns,
              },
            ]
          : [];
      state.autocompleteObjectNames = objects.map((item) => item.name);
      await route.fulfill({ json: { parameters: [], macros: [], config_keys: [], objects } });
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
          model: modelObject,
        },
      });
      return;
    }

    if (path === `/api/v1/projects/${PROJECT_ID}/models/${MODEL_ID}` && method === "PUT") {
      const payload = request.postDataJSON() as { model?: typeof modelObject };
      if (payload.model) {
        modelObject = payload.model;
      }
      state.modelSaveCount += 1;
      await route.fulfill({ json: { project_id: PROJECT_ID, model_id: MODEL_ID, path: `model/${MODEL_ID}/model.yml`, model: modelObject } });
      return;
    }

    if (path === "/api/v1/catalog" && method === "GET") {
      if (!catalogUploaded) {
        await route.fulfill({ json: { available: false, meta: null } });
        return;
      }
      await route.fulfill({
        json: {
          available: true,
          meta: {
            source_filename: "catalog.xlsx",
            version_label: null,
            loaded_at: new Date().toISOString(),
            entity_count: 1,
            attribute_count: catalogEntity.attributes.length,
          },
        },
      });
      return;
    }

    if (path === "/api/v1/catalog/upload" && method === "POST") {
      catalogUploaded = true;
      state.catalogUploaded = true;
      await route.fulfill({
        json: {
          available: true,
          meta: {
            source_filename: "catalog.xlsx",
            version_label: null,
            loaded_at: new Date().toISOString(),
            entity_count: 1,
            attribute_count: catalogEntity.attributes.length,
          },
        },
      });
      return;
    }

    if (path === "/api/v1/catalog/entities" && method === "GET") {
      if (!catalogUploaded) {
        await route.fulfill({ status: 404, json: { detail: "Catalog not loaded" } });
        return;
      }
      const search = (url.searchParams.get("search") ?? "").toLowerCase();
      const entityMatches = !search || catalogEntity.name.toLowerCase().includes(search) || catalogEntity.display_name.toLowerCase().includes(search);
      const entities = entityMatches
        ? [
            {
              name: catalogEntity.name,
              display_name: catalogEntity.display_name,
              module: catalogEntity.module,
              attribute_count: catalogEntity.attributes.length,
            },
          ]
        : [];
      await route.fulfill({ json: { entities, total: entities.length } });
      return;
    }

    if (path === `/api/v1/catalog/entities/${catalogEntity.name}` && method === "GET") {
      if (!catalogUploaded) {
        await route.fulfill({ status: 404, json: { detail: "Catalog not loaded" } });
        return;
      }
      await route.fulfill({ json: catalogEntity });
      return;
    }

    if (path === "/api/v1/admin/templates" && method === "GET") {
      await route.fulfill({ json: [{ name: "flx" }] });
      return;
    }

    if (path === "/api/v1/admin/templates/flx" && method === "GET") {
      await route.fulfill({
        json: {
          name: "flx",
          content: "template: flx",
          rules: { folders: [{ name: "01_stage", materialized: "insert_fc", enabled: true }] },
        },
      });
      return;
    }

    if (path === "/api/v1/admin/rules" && method === "GET") {
      await route.fulfill({
        json: {
          rules: [{ id: "R1", name: "Rule 1", severity: "warning", pattern: "select", enabled: true, description: "mock rule" }],
        },
      });
      return;
    }

    if (path === "/api/v1/admin/macros" && method === "GET") {
      await route.fulfill({ json: { macros: [] } });
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
  return state;
}

test.beforeEach(async ({ page }) => {
  currentMockState = await mockApi(page);
});

test("critical path: open project to lineage", async ({ page }) => {
  await page.goto("/");
  await openProjectWorkspace(page);
  await page.locator("nav.tabbar").getByRole("button", { name: /Lineage/i }).click();
  await expect(page.locator(".workbench").getByText("Lineage", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("1 folders").first()).toBeVisible();
  await expect(page.getByText("01_stage").first()).toBeVisible();
});

test("critical path: edit sql, save and validate", async ({ page }) => {
  await page.goto("/");
  await openProjectWorkspace(page);
  await page.locator("nav.tabbar").getByRole("button", { name: /Lineage/i }).click();
  await page.getByRole("button", { name: /Open →/ }).first().click();
  await expect(page.getByRole("heading", { name: /SQL Editor: 001_main\.sql/i })).toBeVisible();
  await page.keyboard.type("\nSELECT 2 AS id");
  await page.getByRole("button", { name: "Save (Ctrl+S)" }).click();
  await page.getByRole("banner").getByRole("button", { name: "Validate" }).click();
  await expect(page.getByText("Validate Screen")).toBeVisible();
});

test("critical path: wizard create and build", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /New project/i }).click();
  await expect(page.locator(".hub-modal")).toBeVisible();
  await expect(page.locator(".hub-modal").getByText("Create project", { exact: true }).first()).toBeVisible();
  await page.locator(".hub-modal input").first().fill("autoe2e");
  await page.locator(".hub-modal").getByRole("button", { name: "Create project" }).click();
  await expect(page.locator(".hub-modal")).toHaveCount(0);
  await openProjectWorkspace(page);
  await page.getByRole("banner").getByRole("button", { name: "Build" }).click();
  await expect(page.getByRole("heading", { name: "Build", exact: true })).toBeVisible();
});

test("model editor sync mode switches and keeps status", async ({ page }) => {
  await page.goto("/");
  await openProjectWorkspace(page);
  await page.locator("nav.tabbar").getByRole("button", { name: /Model editor/i }).click();
  await expect(page.getByRole("heading", { name: "Model Editor" })).toBeVisible();
  await expect(page.getByText("schema:")).toBeVisible();
  await page.getByRole("button", { name: "YAML" }).click();
  await expect(page.getByRole("heading", { name: "YAML Mode" })).toBeVisible();
  await page.getByRole("button", { name: "Visual" }).click();
  await expect(page.getByRole("heading", { name: "Target Table" })).toBeVisible();
});

test("catalog flow: upload, import fields, save and refresh autocomplete", async ({ page }) => {
  const state = currentMockState;
  await page.goto("/");
  const catalogShortcut = page.getByRole("button", { name: "Data Catalog" });
  if ((await catalogShortcut.count()) > 0) {
    await catalogShortcut.first().click();
  }
  const catalogPanel = page.locator(".catalog-panel").first();
  await catalogPanel.scrollIntoViewIfNeeded();
  const uploadCatalogButton = catalogPanel.getByRole("button", { name: /Upload \.xlsx|Replace catalog/i });
  if ((await uploadCatalogButton.count()) === 0) {
    const catalogToggle = catalogPanel.locator(".catalog-panel-head").getByRole("button").first();
    await catalogToggle.click();
  }

  const uploadInput = page.locator('input[type="file"][accept=".xlsx"]').first();
  await uploadInput.setInputFiles({
    name: "catalog.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: Buffer.from("fake-catalog"),
  });
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByText("catalog.xlsx")).toBeVisible();
  await expect.poll(() => state.catalogUploaded).toBe(true);
  await openProjectWorkspace(page);

  await page.locator("nav.tabbar").getByRole("button", { name: /Model editor/i }).click();
  await expect(page.getByRole("heading", { name: "Model Editor" })).toBeVisible();
  await page.getByRole("button", { name: /Import from catalog/i }).click();
  await expect(page.getByRole("heading", { name: "Import fields from catalog" })).toBeVisible();
  await page.getByRole("button", { name: "Import fields" }).click();

  await expect(page.getByText("Last import from")).toContainText("Account");
  await expect(page.getByRole("cell", { name: "account_id" }).first()).toBeVisible();
  await expect.poll(() => state.modelSaveCount).toBeGreaterThan(0);

  const autocompleteRequestsBeforeSqlTab = state.autocompleteRequestCount;
  await page.locator("nav.tabbar").getByRole("button", { name: /SQL editor/i }).click();

  await expect.poll(() => state.autocompleteObjectNames).toContain("Account");
  await expect.poll(() => state.autocompleteRequestCount).toBeGreaterThan(autocompleteRequestsBeforeSqlTab);
});
