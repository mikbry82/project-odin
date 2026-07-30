# Changelog

All notable changes to Project Odin are documented in this file.

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
