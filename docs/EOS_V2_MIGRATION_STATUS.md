# EOS / 2TO — Single Project Consolidation Status

## Decision

The repository is now treated as **one deployable project**. The canonical runtime is the root `main.py`; the canonical frontend source is `frontend/`.

`eos_v2/` is retained only as an internal architecture/library being progressively integrated into the root application. It is not a second deployable project.

## Completed in this consolidation step

- Removed the nested `erp-system/` project tree.
- Removed the nested `eos-system/` project tree.
- Promoted `erp-system/frontend/` to the repository-root `frontend/` path so its real metadata-driven UI and authentication work are not discarded.
- Updated the root Docker build to install/build `frontend/` and serve `frontend/dist`.
- Updated frontend CI to build/test `frontend/` rather than the deleted nested path.
- Kept the broad root backend runtime and its API surface intact while convergence proceeds.

## Important architectural rule

There is one product, one runtime entrypoint, one frontend source, one deployment pipeline and one repository. `eos_v2/` is not independently deployable and must not acquire a second deployment path.

## Remaining convergence work

- Integrate proven v2 domain/application/infrastructure capabilities into the root runtime without losing existing production capabilities.
- Remove duplicate legacy router/engine implementations only after their behavior is represented by the unified application layer and regression tests pass.
- Consolidate database migration ownership into one authoritative migration path.
- Make the v2 PostgreSQL/API E2E path run through the root application.
- Remove remaining obsolete v2-specific deployment/workflow artifacts once their checks are incorporated into the single root CI.
- Run the complete root CI and frontend certification before merging this branch.

## Non-negotiable

No functionality is deleted merely to make the tree look clean. A component may be removed only after its behavior is either migrated into the unified root application or proven redundant by tests.
