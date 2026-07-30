# Project Odin v0.9.0

Project Odin is an explainable market-analysis and paper-trading application. The
v0.9.0 desktop release candidate packages the existing React frontend and FastAPI
backend into a Windows application without changing trading logic, recommendations,
strategies, API payloads, or the database schema.

Live trading remains locked. News and macro agents remain visibly offline until
verified data sources are available.

## Desktop release candidate

The Windows application:

- opens in its own Electron window;
- starts a localhost-only packaged backend automatically;
- waits for backend and database health before showing the interface;
- stores desktop data locally in the Electron user-data directory;
- avoids duplicate desktop and backend processes;
- requests graceful backend shutdown when the window closes.

Generated Windows artifacts:

- `frontend/release/Project-Odin-Setup-0.9.0-x64.exe`
- `frontend/release/Project-Odin-Portable-0.9.0-x64.exe`

The installer supports a user-selected installation directory. The portable build can
run without installation.

## Desktop development

Requirements:

- Node.js 22 or newer
- Python 3.13 or newer

Install dependencies:

```powershell
cd backend
python -m pip install -e ".[dev]"

cd ..\frontend
npm install
```

Run Electron with the Vite development server and an automatically managed local
backend:

```powershell
cd frontend
npm run dev:desktop
```

Normal browser development remains available:

```powershell
cd frontend
npm run dev
```

In another terminal:

```powershell
cd frontend
npm run dev:backend
```

Then open `http://127.0.0.1:5173`.

## Windows builds

Build the frontend, packaged backend, and unpacked Electron application:

```powershell
cd frontend
npm run build:desktop
```

Create the NSIS installer and portable executable:

```powershell
cd frontend
npm run package:desktop
```

The packaged backend can be built separately with:

```powershell
cd frontend
npm run build:backend
```

## Docker

Copy `.env.example` to `.env`, replace the PostgreSQL password placeholders, and run:

```powershell
docker compose up --build
```

Open `http://localhost:5173`. Docker continues to use PostgreSQL and the existing
browser-based development workflow.

## Configuration

Desktop mode supplies safe runtime values automatically:

- backend host: `127.0.0.1`
- backend port: `8000`
- database: local SQLite file in Electron's user-data directory
- allowed renderer origin: `app://odin`

Docker uses `DATABASE_URL` from `.env`. Never commit `.env`, database files, exchange
credentials, or other secrets. Configuration validation does not include secret input
values in errors.

## Troubleshooting

### Port 8000 is already in use

Project Odin reuses an already-healthy Odin backend but will not take over an unrelated
process. Close the process using port 8000 and restart the application:

```powershell
Get-NetTCPConnection -LocalPort 8000
```

### Odin cannot start within 30 seconds

Restart the application. If the issue remains, confirm that security software has not
blocked the packaged backend and that the user-data directory is writable.

### Windows displays a SmartScreen warning

The v0.9.0 release-candidate artifacts are not signed with a trusted publisher
certificate. Only run artifacts built from a trusted checkout.

### Docker health check fails

Confirm PostgreSQL is healthy and that `DATABASE_URL` uses the same database name,
user, and password configured for the `db` service.

## Security posture and known limitations

- Electron uses `contextIsolation`, renderer sandboxing, disabled Node integration,
  denied permission requests, blocked new windows, and restricted navigation.
- The renderer receives no IPC or shell-access API.
- Production UI assets load only from the packaged `app://odin` origin.
- The backend binds only to localhost in desktop mode.
- The localhost API has no authentication; another process running as the same user
  could attempt local requests.
- The local SQLite database is not encrypted at rest.
- Windows artifacts use Electron's default placeholder icon and are not
  publisher-signed.
- Automatic updates and crash reporting are not included.

These packaging, signing, local-authentication, and data-at-rest items should be
reviewed before v1.0.

## Verification

Frontend and desktop:

```powershell
cd frontend
npm run format:check
npm run lint
npm run build
npm run build:desktop
npm run package:desktop
```

Backend:

```powershell
cd backend
python -m ruff format --check app tests ..\scripts\build_desktop_backend.py
python -m ruff check app tests ..\scripts\build_desktop_backend.py
python -m compileall -q app tests
python -m pytest -q
python -m pip wheel . --no-deps --no-build-isolation
```

See [CHANGELOG.md](CHANGELOG.md) for detailed release notes.
