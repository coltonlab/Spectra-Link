# K-Analysis Dashboard Refactor Plan

## Goal
Reduce the size and complexity of the K-analysis dashboard so it is easier to maintain and cheaper for automated changes to reason about.

## Target structure
1. Keep the main dashboard as the controller/orchestrator.
2. Move all widget/layout construction into a dedicated UI module.
3. Move all fitting and K-analysis calculations into a dedicated analysis module.
4. Keep data/state handling inside the dashboard but use helper functions where appropriate.

## Execution status
- [x] Extract UI construction into a dedicated module.
- [x] Extract fitting and K-analysis logic into a dedicated module.
- [x] Keep the main dashboard focused on orchestration and interaction flow.
- [x] Add a smoke test around the new UI module.
