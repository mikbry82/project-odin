# Changelog

All notable changes to Project Odin are documented in this file.

## [1.0.0] - 2026-07-30

First stable production release. This release is limited to release hardening,
version consistency, artifact hygiene, verification, and documentation. Trading
logic, recommendations, strategy calculations, API contracts, and the database
schema are unchanged.

### Changed

- Updated application, package, backend, visible UI, installer, and portable
  artifact versions to 1.0.0.
- Prevented the Electron development mode exception from being enabled in a
  packaged build.
- Removed tracked generated Python package metadata and ignored future
  `*.egg-info` output.
- Updated installation, first-start, development, Docker, troubleshooting, storage,
  security, limitations, and financial-responsibility documentation.

### Verification

- Frontend formatting, lint, build, Electron syntax, unpacked desktop build, and
  Windows packaging pass.
- Backend formatting, lint, compilation, all 15 tests, wheel build, and packaged
  startup/shutdown/failure-path checks pass.
- Docker Compose validation was unavailable because Docker is not installed.
- Installer installation and 1.0.0 metadata checks pass; automated installer and
  portable UI lifecycle testing remains gated by the non-interactive test
  environment and must be completed manually before release.
- Full results and checksums are recorded in `RELEASE_NOTES_1.0.0.md`.
- Windows artifacts:
  `Project-Odin-Setup-1.0.0-x64.exe` and
  `Project-Odin-Portable-1.0.0-x64.exe`.

### Known limitations

- Windows artifacts are not publisher-signed and use Electron's default icon.
- Localhost API requests are not authenticated.
- Desktop SQLite data is not encrypted at rest.
- Automatic updates and crash reporting are not included.

## [0.9.0] - 2026-07-30

Windows desktop release candidate focused on packaging, startup reliability,
configuration, and security. Trading logic, recommendations, strategy calculations,
API payloads, and the database schema are unchanged.

### Added

- Secure Electron shell for the existing React and FastAPI application.
- Automatic localhost backend startup, readiness polling, single-instance handling,
  port-conflict detection, and graceful shutdown.
- Swedish desktop startup, timeout, configuration, port-conflict, and unexpected-exit
  messages.
- PyInstaller backend executable using desktop-only local SQLite configuration.
- Electron development, unpacked build, NSIS installer, and portable build scripts.
- Windows installer and portable executable packaging metadata.

### Changed

- Registered the existing `/health` router used by Docker and desktop readiness checks.
- Added validated desktop host, port, and CORS configuration with hidden validation
  inputs.
- Restricted Docker and desktop backend startup to explicit host configurations;
  desktop mode binds to `127.0.0.1`.
- Updated all package and application metadata to v0.9.0.

### Security

- Enabled `contextIsolation`, renderer sandboxing, and `webSecurity`.
- Disabled Node integration and exposed no renderer IPC surface.
- Denied permission requests, new windows, webviews, and navigation outside the
  packaged origin or local Vite development origin.
- Added restrictive Content Security Policies for startup and application pages.
- Kept secrets out of renderer configuration and sanitized startup errors.

### Files affected

- `.env.example`
- `.gitignore`
- `backend/app/core/config.py`
- `backend/app/desktop.py`
- `backend/app/main.py`
- `backend/pyproject.toml`
- `backend/project_odin_backend.egg-info/PKG-INFO`
- `frontend/electron/`
- `frontend/index.html`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.ts`
- `scripts/build_desktop_backend.py`
- `README.md`
- `CHANGELOG.md`

### Verification

- Frontend Prettier check, TypeScript lint, and Vite production build pass.
- Electron scripts pass syntax checks and the unpacked Electron build succeeds.
- Packaged backend health and graceful-shutdown smoke test passes.
- Packaged Electron lifecycle smoke test passes.
- Backend Ruff formatting, Ruff lint, compilation, and all 15 tests pass.
- Backend v0.9.0 wheel build passes.
- Docker Compose parsing and `git diff --check` pass.
- Created `Project-Odin-Setup-0.9.0-x64.exe`.
- Created `Project-Odin-Portable-0.9.0-x64.exe`.

### Known limitations

- Windows artifacts are not publisher-signed and use Electron's default icon.
- Localhost API requests are not authenticated.
- Desktop SQLite data is not encrypted at rest.
- Automatic updates and crash reporting are not included.

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
