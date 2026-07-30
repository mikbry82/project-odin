# Project Odin 1.0.0 release notes

## Summary

Project Odin 1.0.0 is the first stable Windows desktop release. It hardens packaging,
startup security, release metadata, repository hygiene, verification, and
documentation while preserving v0.9.0 product behavior. Trading logic,
recommendations, strategy calculations, API contracts, and the database schema are
unchanged.

## Installation

- Installer: run `Project-Odin-Setup-1.0.0-x64.exe`, select an installation
  directory, then launch Project Odin from its shortcut.
- Portable: run `Project-Odin-Portable-1.0.0-x64.exe` directly.
- The unsigned builds may display a Windows SmartScreen warning. Only run artifacts
  from a trusted source.
- First start creates the local database in the per-user Project Odin application
  data directory and may take longer than subsequent starts.

## SHA-256 checksums

- `Project-Odin-Setup-1.0.0-x64.exe`:
  `746ABA355FD1D9D74190B15DE1F52365AFF1E47D0C5676DF81786866B341D707`
- `Project-Odin-Portable-1.0.0-x64.exe`:
  `A49DD924B6B2A60BEE6F128B6AEAD2BA1452AB80CF6A6D336FA1E74A83A7A661`

## Upgrade from v0.9.0

Close v0.9.0 before installing or starting v1.0.0. The application continues to use
the existing per-user desktop data location and database schema. Keep a backup of
important local data before upgrading. The portable executable may be placed beside
or instead of the previous portable build; do not run both versions simultaneously.

## Known limitations

- Windows artifacts are not publisher-signed and use Electron's default icon.
- The localhost API is not authenticated.
- The local SQLite database is not encrypted at rest.
- Automatic updates, telemetry, cloud services, and crash reporting are not
  included.
- Live trading is locked; market analysis and paper trading remain the supported
  modes.
- Market data may be delayed, incomplete, or unavailable.

Project Odin is not financial advice. All financial decisions and their consequences
remain the user's responsibility.

## Verification

Frontend formatting, TypeScript lint, Vite production build, Electron syntax checks,
unpacked desktop build, and installer/portable packaging passed. Backend Ruff
formatting and lint, compilation, all 15 tests, wheel creation, packaged-backend
startup/readiness, shutdown, restart, port-conflict, and invalid-configuration tests
passed. Production npm dependencies report zero known vulnerabilities.

Docker Compose validation was not run because Docker is unavailable. The installer
successfully updated the installed application and Windows uninstall metadata to
1.0.0. Automated UI lifecycle testing of the installed and portable executables
could not be completed in the current non-interactive execution environment: the
Electron GUI process exited before a UI readiness signal could be observed. The
release therefore remains gated pending manual installer and portable UI lifecycle
verification on an interactive Windows desktop.
