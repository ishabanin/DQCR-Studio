# DQCR Studio - Lineage UX Spec

**Document:** `LINEAGE_UX_SPEC.md`  
**Version:** 1.0 · March 2026  
**Purpose:** A self-contained UX and implementation brief for improving the `Lineage` screen in DQCR Studio.

> This document describes the current screen, key UX issues, the target interaction model, and acceptance criteria. It is intended for an agent or engineer who will redesign and refine the Lineage experience without breaking existing functionality.

---

## 1. Screen Purpose

The `Lineage` screen helps a user understand one selected model as a dependency graph of workflow folders.

The screen should answer these questions quickly:

- Which folders exist inside the selected model workflow
- How those folders depend on each other
- Which SQL files belong to each folder
- Which parameters and CTEs are used by the selected folder
- Which nodes are active for the current context selection
- Whether the graph is based on fresh workflow cache or fallback file structure

This is an analysis and navigation screen, not an editor.

---

## 2. Current Implementation

### 2.1 Source Files

- Screen container: `frontend/src/features/lineage/LineageScreen.tsx`
- Graph renderer: `frontend/src/features/lineage/DagGraph.tsx`
- Graph layout helpers: `frontend/src/features/lineage/dagLayout.ts`
- Shared styles: `frontend/src/styles.css`

### 2.2 Current Data Flow

The screen loads:

1. Project tree via `fetchProjectTree(projectId)`
2. Model lineage via `fetchModelLineage(projectId, modelId, context?)`
3. Workflow status via `fetchProjectWorkflowStatus(projectId)`

The model list is derived from the `model/` or `models/` folder in the project tree.

The selected model is local state. If the current model disappears or is empty, the first available model becomes active automatically.

### 2.3 Context Logic

The screen depends on `contextStore`:

- If `multiMode === false`, lineage data is requested for one `activeContext`
- If `multiMode === true`, lineage is requested without a single context and then filtered on the client using `activeContexts`

Node visibility rule:

- `enabled_contexts === null` means always visible
- otherwise the node must match at least one active context

Edges are filtered after nodes. Only edges with both endpoints visible remain in the graph.

### 2.4 Current Screen Structure

The current visual order is:

1. Page title `Lineage`
2. Toolbar
3. Fallback warning banner when workflow source is stale
4. Loading or error text for lineage request
5. Summary badges
6. Main two-column layout
7. Empty text if no nodes remain after filtering

### 2.5 Current Toolbar

The toolbar currently contains:

- Model select
- View mode switch: `Horizontal`, `Vertical`, `Compact`
- Search input with placeholder `Search folders...`
- `Export PNG` button

Toolbar behavior is functional but visually flat. Controls are not grouped by meaning.

### 2.6 Current Graph Area

The graph is rendered with React Flow and dagre.

Current technical behavior:

- fixed canvas height: `460px`
- `fitView` enabled
- min zoom: `0.4`
- max zoom: `1.8`
- canvas panning enabled
- scroll zoom enabled
- nodes are not draggable
- edges use `smoothstep`
- edges end with arrow markers

Layout directions:

- `horizontal` -> dagre `LR`
- `vertical` -> dagre `TB`
- `compact` -> still `LR`, but nodes are visually simplified

### 2.7 Current Node Design

Standard node contains:

- folder name
- materialization badge
- up to 4 SQL chips
- `+N` chip when queries exceed 4

Compact node contains:

- folder name only

Selected node gets accent border styling.

### 2.8 Current Detail Panel

The detail panel appears only when a node is selected.

It currently shows:

- node name
- materialization
- parameters list
- CTE list
- buttons `Open {queryName}` for each SQL file

Clicking an `Open` button:

- opens `${selectedNode.path}/${queryName}`
- switches to SQL tab

### 2.9 Current Summary

Three badges are displayed above the graph:

- `{folders} folders`
- `{queries} queries`
- `{params} params`

These values come from lineage API summary and represent the selected model as a whole, not the filtered graph currently visible on screen.

### 2.10 Current States

Current states are plain text:

- No project selected
- Project tree loading
- Project tree error
- No models found
- Lineage loading
- Lineage error
- No nodes after context/search filtering

These states are informative but not product-quality from a UX perspective.

---

## 3. Current UX Issues

### 3.1 Information Hierarchy

The screen lacks a strong top-level summary. A user does not immediately see:

- which model is active
- which context mode is affecting the graph
- whether the graph is filtered
- whether the graph is complete or fallback-based

### 3.2 Toolbar Clarity

The toolbar is a flat row of controls. It does not visually separate:

- model selection
- graph layout controls
- filtering tools
- export action

### 3.3 Selection Experience

The detail panel is useful only after selection, but the screen does not strongly prompt the user to select a node when nothing is selected.

### 3.4 Search UX

Search currently matches only `node.name`. It does not search:

- path
- SQL query names
- parameter names
- CTE names

This makes search weaker than user expectations for a graph exploration screen.

### 3.5 Filter Visibility

The user cannot easily tell:

- how many nodes are hidden by context
- how many are hidden by search
- whether the summary badges reflect the filtered result or full result

### 3.6 Graph Readability

The graph canvas has a fixed height and limited environmental context:

- no legend for edge colors
- no hint for what `Compact` mode means
- no quick reset/focus affordances
- no inline explanation for materialization badge

### 3.7 Fallback Awareness

The fallback banner exists, but it is visually secondary and may be missed. This is risky because fallback data can change how much the user trusts the graph.

### 3.8 Empty and Error States

States are correct logically but too raw visually. They do not help the user recover.

---

## 4. UX Goals

The improved `Lineage` screen should feel like a graph exploration workspace.

Primary goals:

- Make the current model and filter state obvious
- Make graph exploration faster
- Reduce ambiguity around context filtering
- Make node selection feel intentional
- Improve trust when data is stale or fallback-based
- Preserve current behavior while improving interaction quality

The redesign should stay compact, technical, and professional. It should not feel like a marketing dashboard.

---

## 5. Target Layout

### 5.1 High-Level Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ Lineage                                                            │
│ Active model, context mode, source freshness, filtered counts      │
├─────────────────────────────────────────────────────────────────────┤
│ [Model v] [Horizontal|Vertical|Compact] [Search....] [Export PNG]  │
├─────────────────────────────────────────────────────────────────────┤
│ Warning banner if fallback / stale cache                           │
├─────────────────────────────────────────────────────────────────────┤
│ 3-5 compact summary badges                                         │
├───────────────────────────────┬─────────────────────────────────────┤
│ Graph canvas                  │ Detail panel                        │
│                               │                                     │
│ React Flow graph              │ Empty prompt or selected node info  │
│                               │                                     │
└───────────────────────────────┴─────────────────────────────────────┘
```

### 5.2 Layout Behavior

Desktop:

- two columns
- graph takes main width
- detail panel is persistent on the right

Tablet and below:

- graph first
- detail panel stacked below

The detail panel should remain present even when no node is selected. In that case it should show an instructional empty state.

---

## 6. Target Screen Sections

### 6.1 Header Block

The top block should show:

- page title `Lineage`
- active model name
- current context mode:
  - single context
  - multi-context
- source status:
  - workflow cache
  - fallback
- optional filtered count, for example:
  - `12 of 18 folders visible`

This area should give immediate situational awareness.

### 6.2 Toolbar Block

Toolbar should be visually grouped into 4 zones:

1. Model selection
2. Graph orientation mode
3. Search and filter
4. Export action

Desired behavior:

- model switch is the strongest control
- layout mode is clearly a segmented control
- search should visually read as a graph filter, not a generic input
- export should be secondary to navigation, but still easy to find

### 6.3 Status Banner

If workflow source is fallback, show a prominent warning banner with:

- clear statement that graph is built from fallback structure
- short explanation that cache may be outdated
- rebuild action

If rebuild is pending:

- banner action should show progress state

The banner should feel important but not alarming.

### 6.4 Summary Row

The summary row should ideally show both full-model and visible-filtered context if filtering is active.

Recommended metrics:

- folders visible
- total queries
- total params
- current layout mode or context scope if useful

If the API summary remains full-model only, the UI should visually clarify that these are model totals.

### 6.5 Graph Area

The graph should remain the primary focus.

Desired qualities:

- clean background
- clear active node state
- comfortable zooming and panning
- obvious edge direction
- visible spatial breathing room

Optional enhancements that fit current architecture:

- reset view button
- fit graph button
- legend for edge status colors
- hover emphasis for node connections

### 6.6 Detail Panel

The detail panel should always exist as a stable surface.

When no node is selected:

- show instruction such as `Select a folder to inspect lineage details`
- optionally show what users can do there

When a node is selected, show:

- node name
- materialization
- full path
- parameters
- CTEs
- query list with open actions
- optional inbound/outbound counts if derivable

The panel should feel like a structured inspector, not a loose stack of text blocks.

---

## 7. Interaction Model

### 7.1 Model Selection

Changing model should:

- reload lineage graph
- update summary
- reset invalid selection if selected node no longer exists

It may preserve view mode and search, but this should be a deliberate choice.

### 7.2 Node Selection

Clicking a node should:

- visually highlight it in the graph
- update detail panel

If no node is selected and nodes exist:

- first visible node may still auto-select, but the UI should make that obvious

### 7.3 Search

Minimum requirement:

- keep current name-based search

Preferred improvement:

- search across node name
- path
- SQL query names

If search is active:

- show visible result count
- provide clear reset affordance

### 7.4 Context Filtering

The UI should clearly indicate whether filtering comes from:

- single active context
- multi-context mode

This should not be hidden knowledge.

### 7.5 Query Opening

Opening SQL from the detail panel is already valuable and should stay.

Improve discoverability by:

- making query rows feel clickable and consistent
- optionally showing query filename without repeating `Open`

### 7.6 Export

Export PNG should remain available.

The UI should clarify whether export captures:

- the visible graph area
- or the full fitted graph canvas

Current implementation exports the graph container rendered in the canvas area.

---

## 8. States

### 8.1 No Project

Instead of plain text, show an empty workspace state:

- title
- short explanation
- suggestion to choose a project

### 8.2 Tree Loading

Show skeleton or structured loading state instead of plain paragraph text.

### 8.3 Tree Error

Show error block with retry affordance if possible.

### 8.4 No Models

Show a dedicated empty state:

- explain that no `model/` folders were found
- optionally hint where models are expected

### 8.5 Lineage Loading

Prefer graph skeleton or loading placeholder in the graph area.

### 8.6 Lineage Error

Show inline error state in the graph area with retry.

### 8.7 Empty After Filter

If search or context filtering leaves zero visible nodes:

- explain why the graph is empty
- offer clear reset actions:
  - clear search
  - change context selection

### 8.8 No Selection

The detail panel should render a friendly inspector-empty state rather than disappearing.

---

## 9. Functional Constraints To Preserve

The redesign must preserve these behaviors:

- model list derived from project tree
- graph built from lineage API
- context-aware node filtering
- edge filtering based on visible nodes
- layout modes `horizontal`, `vertical`, `compact`
- PNG export
- fallback rebuild action
- open SQL file from selected node
- responsive single-column layout below large desktop widths

---

## 10. Non-Goals

This UX task should not introduce:

- graph editing
- manual edge creation
- inline SQL editing inside Lineage
- changes to lineage backend contract unless explicitly required
- replacement of React Flow unless there is a compelling technical reason

---

## 11. Suggested UX Improvements

These are recommended, not mandatory, but strongly aligned with the screen purpose:

- Persist `viewMode` per user or per project
- Persist last selected model inside the session
- Add graph legend for edge status colors
- Add clear empty inspector state
- Add filtered result copy, for example `Showing 8 of 14 folders`
- Make summary distinguish `visible` vs `total`
- Add `Reset view` control near graph
- Add `Clear search` affordance inside search field
- Improve detail panel typography and grouping
- Show path for selected node
- Make query actions more compact and scannable

---

## 12. Acceptance Criteria

### Structure and Clarity

- [ ] The active model is obvious without reading the select control carefully
- [ ] The screen clearly communicates whether data comes from workflow cache or fallback
- [ ] The screen clearly communicates whether context filtering is affecting the graph
- [ ] The toolbar is visually grouped by purpose

### Graph UX

- [ ] Graph remains the primary visual focus
- [ ] Selected node state is obvious
- [ ] Detail panel remains present even when no node is selected
- [ ] Layout modes are understandable and easy to switch
- [ ] Search meaning is clear to the user

### States

- [ ] No project state is a designed empty state
- [ ] No models state is a designed empty state
- [ ] Loading state is not plain paragraph text only
- [ ] Error state is not plain paragraph text only
- [ ] Zero-results state explains why the graph is empty

### Actions

- [ ] Rebuild action remains available when fallback source is shown
- [ ] Export PNG remains available
- [ ] Opening SQL from selected query still works
- [ ] Model switch still works

### Responsiveness

- [ ] Desktop uses graph + inspector two-column layout
- [ ] Smaller screens stack graph and inspector cleanly
- [ ] Toolbar wraps without becoming confusing

---

## 13. Implementation Notes For Agent

When improving UX, prefer:

- component extraction for header, toolbar, summary, graph panel, and detail panel
- keeping business logic in `LineageScreen.tsx`
- keeping React Flow rendering inside `DagGraph.tsx`
- avoiding backend changes unless the UX is blocked without them

If additional metadata is needed for better UX, the safest first additions would be:

- node path in the detail panel
- visible node count
- visible edge count
- optional upstream/downstream counts derived on the client

---

## 14. Short Design Direction

The screen should feel:

- analytical
- technical
- structured
- calm
- dense but readable

It should not feel:

- like a generic dashboard
- like a dev-only debug page
- like a form-heavy admin screen

The target impression is a professional graph inspector for data engineers.

---

## 15. Deliverable Expectation

A successful UX pass should leave the screen with:

- stronger hierarchy
- better affordance for selection and filtering
- clearer trust signals
- higher scanability
- better empty/loading/error states

without changing the core user workflow.
