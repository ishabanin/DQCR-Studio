# SQL Autocomplete Agent Spec

## Goal

Add schema-aware autocomplete to `SQL Editor` so the editor can suggest:

- project objects
- workflow query references
- local CTEs
- columns for aliased objects and CTEs
- existing DQCR parameters, macros, and `@config` snippets

This phase is intentionally limited to project-local metadata. External catalog integration is explicitly deferred.

## User Problem

The current editor only suggests:

- DQCR parameters
- macro names
- `@config` keys and snippets

It does not know about SQL objects or their attributes, so completions after `FROM`, `JOIN`, `UPDATE`, `INTO`, or `alias.` are not context-aware.

## Phase 1 Scope

### Included

- Project target tables from all models in the current project
- Workflow query references for the active model only
- Local CTE names from the currently opened SQL file
- Local CTE columns inferred from the current SQL text
- Column suggestions after `alias.`
- Object suggestions in object-introduction contexts:
  - `FROM`
  - `JOIN`
  - `UPDATE`
  - `INTO`

### Excluded

- External catalog objects
- Live database introspection
- SQL validation or semantic error checking
- Join condition generation
- AI/LLM-generated schema inference

## Design Principles

### Deterministic over generative

Autocomplete must use structured metadata, not LLM output.

### Project-safe fallback

If workflow cache is unavailable for a model, autocomplete must still expose at least the model target table from `model.yml`.

### Context-sensitive, not global noise

Object suggestions should be prioritized in object contexts, and column suggestions should be prioritized after `alias.`. Existing DQCR completions must remain available.

### Stable contract for later catalog merge

The response shape must be designed so external catalog objects can be added later without frontend redesign.

## Backend Contract

Endpoint:

- `GET /api/v1/projects/{project_id}/autocomplete`

Query params:

- `model_id` optional

### Response shape

The response must continue returning:

- `parameters`
- `macros`
- `config_keys`
- `all_contexts`
- `data_source`
- `fallback`

The response must be extended with:

- `objects`

### Object payload

Each object entry must contain enough metadata for lookup, ranking, and column completions.

Required fields:

- `name`: canonical insert value
- `kind`: `target_table` or `workflow_query`
- `source`: `project_workflow` or `project_model_fallback`
- `model_id`
- `path`
- `lookup_keys`
- `columns`

Column entries must contain:

- `name`
- `domain_type`
- `is_key`

### Object collection rules

#### Target tables

- Collect target tables from every model in the project.
- Prefer workflow cache when available.
- Fallback to `model.yml` parsing when workflow cache is unavailable.
- Expose both fully qualified and short lookup keys when possible:
  - `schema.table`
  - `table`

#### Workflow queries

- Collect only for the active `model_id`.
- Build canonical names as `_w.<folder>.<query>`.
- Exclude synthetic CTE steps and non-query synthetic steps.
- Use `sql_model.attributes` as the primary source of columns.
- If `sql_model.attributes` is empty, fallback to `sql_model.metadata.aliases`.

### Fallback semantics

- `fallback = true` if any model had to fallback while assembling the response.
- `data_source = "fallback"` when fallback happened, otherwise `"workflow"`.

## Frontend Contract

The Monaco language layer must accept the extended autocomplete payload and maintain all existing completions.

### Dynamic autocomplete state

The editor must store:

- parameters
- macros
- config keys
- project objects
- active model id

### Local SQL analysis

The frontend must parse the current SQL text to derive:

- local CTE names
- local CTE columns
- alias to object mapping from `FROM/JOIN/UPDATE/INTO`

This analysis is heuristic and lightweight. It is not a full SQL parser.

## Completion Behavior

### Macro context

Inside `{{ ... }}`:

- suggest parameters
- suggest macros

### Object context

After `FROM`, `JOIN`, `UPDATE`, or `INTO`:

- suggest local CTEs first
- suggest project objects next
- prefer objects from the active model

### Member context

After `alias.`:

- resolve alias to local CTE or project object
- suggest matching columns

If no alias match is found:

- do not force unrelated column suggestions

### Non-contextual fallback

Outside object/member contexts:

- keep `@config` and template snippets available
- allow Monaco quick suggestions to surface object names while typing

## Ranking Rules

Highest priority:

- local CTE columns for a matched alias
- local CTE names in object context

Then:

- active-model workflow queries
- active-model target tables
- other project target tables

Lowest:

- generic snippets and config keys

## Trigger Rules

The completion provider must trigger on:

- `{`
- `@`
- `:`
- `.`

The `.` trigger is mandatory for `alias.<column>` completion.

## Non-Goals For This Phase

- `_m.*` external object completion
- schema browsing from `md_entity2table`
- cross-project shared catalogs

These are phase 2 and must layer onto the same `objects` contract rather than replacing it.

## Files Expected To Change

- `backend/app/routers/projects.py`
- `frontend/src/api/projects.ts`
- `frontend/src/features/sql/SqlEditorScreen.tsx`
- `frontend/src/features/sql/dqcrLanguage.ts`
- tests for backend and frontend autocomplete behavior

## Acceptance Criteria

- `/autocomplete` returns `objects` with project-local metadata
- `alias.` shows object columns
- local CTE names are suggested in object contexts
- local CTE columns are suggested after aliasing the CTE
- workflow query references for the active model are suggested as `_w.*`
- existing parameter/macro/config completions still work
- fallback mode still returns useful target table objects
