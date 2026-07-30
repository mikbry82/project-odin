# Project Odin v1.0.0

Project Odin is an explainable market-analysis and paper-trading application. The
Windows desktop application packages the React frontend and FastAPI backend and runs
entirely on the local computer. Live trading remains locked, and news and macro
agents remain offline until verified data sources are available.

## Install and start on Windows

Download `Project-Odin-Setup-1.0.0-x64.exe`, run it, choose an installation
directory, and launch Project Odin from the Start menu or desktop shortcut. Windows
SmartScreen may warn because the application is not publisher-signed; only run an
artifact obtained from a trusted source.

For use without installation, download
`Project-Odin-Portable-1.0.0-x64.exe` and run it directly.

On first start, Project Odin starts its localhost backend, creates the local SQLite
database, waits for both backend and database readiness, and then displays the
interface. This can take a little longer than later starts. No terminal window is
required.

Desktop data is stored in Electron's per-user application-data directory under
`Project Odin`. Uninstalling the application does not necessarily delete this data.

## Desktop development

Requirements:

- Node.js 22.12 or newer
- Python 3.13 or newer

Install dependencies:

```powershell
cd backend
python -m pip install -e ".[dev]"

cd ..\frontend
npm ci
```

Run Electron with Vite and the automatically managed local backend:

```powershell
cd frontend
npm run dev:desktop
```

Browser development remains available by running `npm run dev` and
`npm run dev:backend` in separate terminals from `frontend`, then opening
`http://127.0.0.1:5173`.

Build the unpacked desktop application or both Windows release artifacts:

```powershell
cd frontend
npm run build:desktop
npm run package:desktop
```

Artifacts are written to `frontend/release-v1.0.0/`.

## Docker

Copy `.env.example` to `.env`, replace the PostgreSQL password placeholders, then
run:

```powershell
docker compose up --build
```

Open `http://localhost:5173`. Docker uses PostgreSQL and the browser-based
development workflow. Stop it with `docker compose down`.

## Troubleshooting

### Port 8000 is already in use

Project Odin reuses an already-healthy Odin backend but will not take over another
process. Close the process using port 8000 and restart:

```powershell
Get-NetTCPConnection -LocalPort 8000
```

### Startup does not finish within 30 seconds

Restart the application. If the issue remains, check that security software has not
blocked the packaged backend and that the application-data directory is writable.

### The local service exits

Restart Project Odin. A local diagnostic log named `odin-backend.log` is stored in
the application-data directory. Review it before reporting a problem, but do not
share secrets or private data.

### Docker health check fails

Confirm PostgreSQL is healthy and that `DATABASE_URL` matches the database name,
user, and password configured for the `db` service.

## Security and known limitations

- Electron isolates and sandboxes the renderer, disables Node integration, denies
  permission requests, blocks new windows and webviews, and restricts navigation.
- Production UI assets load from the packaged `app://odin` origin.
- The desktop backend binds only to `127.0.0.1`.
- The localhost API has no authentication; another process running as the same user
  could attempt local requests.
- The local SQLite database is not encrypted at rest.
- Windows artifacts use Electron's default icon and are not publisher-signed.
- Automatic updates, telemetry, cloud services, and crash reporting are not
  included.
- Project Odin performs analysis and simulated paper trading only. Market data may
  be delayed, incomplete, or unavailable.

Project Odin is not financial advice. All financial decisions and their consequences
remain the user's responsibility.

## Verification

Release verification covers formatting, linting, production builds, Electron syntax,
backend compilation and tests, wheel creation, Docker Compose parsing, desktop
packaging, and installer/portable lifecycle smoke tests. Exact v1.0.0 results and
artifact checksums are recorded in [CHANGELOG.md](CHANGELOG.md) and
[RELEASE_NOTES_1.0.0.md](RELEASE_NOTES_1.0.0.md).
