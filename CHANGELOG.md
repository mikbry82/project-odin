# Changelog

All notable changes to Project Odin are documented in this file.

## [0.8.3] - 2026-07-30

Test-stability release with no changes to production endpoints, database behavior,
trading logic, recommendations, or strategy calculations.

### Fixed

- Updated the market fallback test to derive its expected count from the configured watchlist.
- Isolated API tests from the production PostgreSQL lifespan with FastAPI dependency overrides.
- Tested the health router in an isolated application instead of assuming production registration.
- Replaced FastAPI internal route-object introspection with stable HTTP status assertions.
- Removed all Docker and external-network requirements from the backend unit suite.

### Files affected

- `backend/tests/conftest.py`
- `backend/tests/test_health.py`
- `backend/tests/test_markets.py`
- `backend/tests/test_system.py`
- `backend/app/main.py`
- `backend/pyproject.toml`
- `backend/project_odin_backend.egg-info/PKG-INFO`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/.prettierignore`
- `frontend/src/App.tsx`
- `README.md`
- `CHANGELOG.md`

### Verification

- Frontend formatting, TypeScript lint, and production build pass.
- Backend Ruff formatting, Ruff lint, compilation, and wheel build pass.
- Backend test suite passes: 15 tests, 0 failures, 0 skips.
- Docker Compose configuration parsing and `git diff --check` pass.

## [0.8.2] - 2026-07-30

Quality-focused release with no new functionality or changes to trading behavior,
strategy calculations, database schemas, or API contracts.

### Changed

- Extracted reusable buttons, cards, badges, loading, error, empty-state, chart, and interval components.
- Centralized frontend API requests and endpoint access behind a typed service.
- Added consistent timeout, network-failure, non-JSON, and invalid-response handling with friendly messages.
- Added shared design tokens for spacing, colors, radii, borders, and shadows.
- Standardized interactive control styling, focus states, disabled states, and status presentation.
- Improved narrow-screen layouts for navigation, tables, scanner actions, strategy controls, and account views.
- Removed unused frontend state, API methods, and action code.
- Reformatted frontend and backend code and simplified duplicated paper-portfolio serialization.

### Files affected

- `frontend/src/App.tsx`
- `frontend/src/api.ts`
- `frontend/src/components/ui.tsx`
- `frontend/src/styles.css`
- `frontend/src/types.ts`
- `frontend/src/utils.ts`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/tsconfig.node.json`
- `frontend/src/vite-env.d.ts`
- `backend/app/`
- `backend/pyproject.toml`
- `.gitignore`
- `CHANGELOG.md`

### Compatibility

- No business logic, API endpoints, request payloads, response schemas, or trading behavior changed.
