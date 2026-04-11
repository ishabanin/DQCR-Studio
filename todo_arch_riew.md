# TODO: Architectural Review Implementation Plan

## Phase 0. Alignment and Safety Net
- [ ] Freeze API contracts for `/projects`, `/ws`, `/files`, `/catalog` and capture current behavior in contract tests.
- [ ] Add smoke tests for build/validate flows (HTTP + WS) before refactoring.
- [ ] Define target architecture in a short ADR (`backend/docs/adr/`): layers, boundaries, dependency direction.

## Phase 1. Critical Contract Fix (POLS)
- [ ] Fix preview endpoint semantic mismatch: `build_id` must not be treated as `engine`.
- [ ] Choose one contract and apply consistently:
- [ ] Option A: rename path param to `engine`.
- [ ] Option B: keep `build_id`, resolve build metadata, read engine from build record.
- [ ] Add regression tests for the chosen contract.

## Phase 2. Dependency Decoupling (DIP/Coupling)
- [ ] Remove cross-router imports from `ws.py` and `files.py` to `projects.py` private functions.
- [ ] Extract shared orchestration use-cases into `backend/app/services/application/`:
- [ ] `build_use_case.py`
- [ ] `validation_use_case.py`
- [ ] `workflow_use_case.py`
- [ ] Replace global `FW_SERVICE` in router with dependency provider/factory (`Depends` or service container).
- [ ] Add unit tests for use-cases with mocked infra dependencies.

## Phase 3. Split God Module (SRP/SoC)
- [ ] Break `routers/projects.py` into cohesive modules:
- [ ] `routers/projects_crud.py`
- [ ] `routers/projects_build.py`
- [ ] `routers/projects_validation.py`
- [ ] `routers/projects_models.py`
- [ ] `routers/projects_parameters.py`
- [ ] Move non-HTTP helpers out of routers into service/domain modules.
- [ ] Keep routers thin: input validation, orchestration call, response mapping only.

## Phase 4. Build/Validation Flow Deduplication (DRY)
- [ ] Create unified app-level methods:
- [ ] `execute_build(request)`
- [ ] `execute_validation(request)`
- [ ] Reuse these methods from both HTTP handlers and WebSocket handlers.
- [ ] Remove duplicated payload normalization and result post-processing logic.

## Phase 5. Replace Ad-hoc YAML Parsing (KISS/Reliability)
- [ ] Replace manual regex/state-machine parsing of `model.yml` with proper YAML parser.
- [ ] Introduce typed schema for model payload (Pydantic models).
- [ ] Implement symmetric read/write adapters:
- [ ] `ModelYamlReader`
- [ ] `ModelYamlWriter`
- [ ] Add round-trip tests (read->write->read) for legacy and canonical formats.

## Phase 6. Global State Hardening (Coupling/Concurrency)
- [ ] Remove mutable in-memory globals for history (`_VALIDATION_HISTORY`, `_BUILD_HISTORY`) from routers.
- [ ] Introduce explicit storage abstraction (`HistoryRepository`).
- [ ] Implement file-based or DB-backed atomic persistence.
- [ ] Add concurrency tests for parallel build/validation updates.

## Phase 7. Engine Extensibility (OCP)
- [ ] Replace engine conditionals with registry/strategy:
- [ ] `EngineRenderer`
- [ ] `EngineBuildPolicy`
- [ ] Register engines declaratively (`dqcr`, `airflow`, `dbt`, `oracle_plsql`).
- [ ] Add a guide and tests for adding a new engine without modifying core orchestration code.

## Phase 8. Catalog DRY Cleanup
- [ ] Remove duplicated entity-search logic from router and use `CatalogService.search_entities(...)`.
- [ ] Keep filtering/sorting/pagination policy in service layer.
- [ ] Add focused tests for search behavior parity.

## Phase 9. Quality Gates
- [ ] Enforce architecture boundaries via import rules (no router->router imports).
- [ ] Add CI checks for:
- [ ] contract tests
- [ ] unit tests for use-cases
- [ ] smoke tests for build/validation and preview
- [ ] Update developer docs with new module map and extension points.

## Definition of Done (for the full initiative)
- [ ] No router imports another router module.
- [ ] `projects.py` no longer contains domain parsing/build orchestration internals.
- [ ] HTTP and WS flows share one orchestration path each for build and validation.
- [ ] Preview endpoint contract is unambiguous and covered by tests.
- [ ] Model YAML IO is parser-based and covered by round-trip tests.
- [ ] History persistence is process-safe and not based on mutable globals.
- [ ] New engine can be added via registry with minimal/no core modifications.
