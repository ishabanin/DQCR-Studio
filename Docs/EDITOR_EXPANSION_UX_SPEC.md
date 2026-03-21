# Editor Expansion UX Spec

## Goal

Add one consistent `Expand` affordance for long-form text editing in two places:

- `SQL Editor`: expand the main query workspace without breaking page context.
- `Parameters > Values > value`: open a temporary large editor for writing long static or dynamic values.

## Interaction Model

### Shared affordance

- Use the same compact icon button `⤢` for expand and `⤡` for collapse.
- Place the button in the top-right area of the editable surface.
- Tooltip and `aria-label` switch between `Expand editor` and `Collapse editor`.

### SQL Editor behavior

- Expansion uses `inline maximize`, not a blocking modal.
- Expanded state keeps the user inside the same screen, with file tabs, breadcrumb, config chain, and save actions still present.
- Expanded state changes the editor area into the primary visual focus and increases usable width and height.
- `Esc` collapses the expanded state.

### Parameter value behavior

- Expansion uses a wide modal editor.
- The inline cell remains compact; expansion is an editing aid, not a permanent layout change.
- Modal uses the same value draft until `Apply`.
- `Esc` closes without applying.
- `Ctrl/Cmd+Enter` applies the current modal content.

## Layout Rules

### SQL Editor

- Default editor height: `420px`.
- Expanded editor height: approximately `76vh` with safe upper bound.
- Expanded state switches the editor column to full-width and moves the inspector below it.

### Value modal

- Modal width: `min(1120px, 94vw)`.
- Modal height: `min(80vh, 860px)`.
- Footer contains `Cancel`, `Apply`, and a compact keyboard hint.

## Accessibility

- Expand buttons are keyboard reachable.
- Modal uses `role="dialog"` and `aria-modal="true"`.
- Close on overlay click.
- Preserve readable mono typography for SQL and multi-line values.

## Implementation Notes

- SQL expansion is local state in `SqlEditorScreen`.
- Parameter expansion is implemented through a reusable modal component so more editors can adopt it later.
- No execute shortcut is introduced for SQL yet because the screen currently has save/format flows, not query execution.
