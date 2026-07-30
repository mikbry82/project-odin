# Project Odin v1.2.1

Project Odin is an explainable market-analysis and paper-trading application. The
Windows desktop application packages the React frontend and FastAPI backend and runs
entirely on the local computer. Live trading remains locked, and news and macro
agents remain offline until verified data sources are available.

Odin uses one complete interface for all users. Technical values, detailed
metrics, diagnostics, market analysis, risk settings, and advanced controls are
always available with understandable Swedish labels and explanations.

## Install and start on Windows

Download `Project-Odin-Setup-1.2.1-x64.exe`, run it, choose an installation
directory, and launch Project Odin from the Start menu or desktop shortcut. Windows
SmartScreen may warn because the application is not publisher-signed; only run an
artifact obtained from a trusted source.

For use without installation, download
`Project-Odin-Portable-1.2.1-x64.exe` and run it directly.

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

Artifacts are written to `frontend/release-v1.2.1/`.

## Manually confirmed Kraken spot trading

Version 1.2.1 includes the disabled-by-default foundation for manually confirmed Kraken
spot purchases. Livekonto provides a searchable multi-select containing active,
backend-approved EUR spot pairs and a manual market/limit purchase form. It does not
enable automatic live trading. Simulation remains the default, and every live order
requires a fresh server-side preview and the explicit button
**Bekräfta riktigt köp**.

Use a dedicated Kraken key with only **Query Funds** and
**Create & modify orders**. Never enable **Withdraw Funds**. Secrets are stored in
the operating-system credential store and are never returned to the frontend after
saving.

Before enabling live confirmation mode, configure the backend-enforced order, daily
amount, order-count, daily-loss, cooldown, pair-allowlist, and optional buy-only
limits. The persistent **NÖDSTOPP LIVE** button is available on every page.

See [LIVE_TRADING_SECURITY.md](LIVE_TRADING_SECURITY.md) before connecting Kraken.
Live trading is not considered safe or complete until the user performs controlled
manual validation with a restricted key.

The optional controlled smoke script never runs in the test suite. After reading the
security guide, run it only from a supervised PowerShell session:

```powershell
$env:ODIN_KRAKEN_MANUAL_SMOKE="I_UNDERSTAND_REAL_MONEY_RISK"
python scripts\kraken_live_smoke.py
```

It performs read-only checks and a validate-only preview first. Press Enter to exit
without an order. A real limit order requires a second exact typed phrase.

## Livekonto och tillåtna tillgångar

Sidan **Livekonto** hämtar saldon, reserverade belopp, öppna spotordrar, senaste
ordrar samt fills och avgifter direkt från Kraken. Portföljvärden i EUR är alltid
markerade som uppskattningar. Odin använder endast ett direkt, aktivt EUR-par för
värdering; tillgångar utan en sådan tillförlitlig väg visas fortfarande med
**Värde saknas**.

Tillgängliga spotpar upptäcks dynamiskt från Krakens `AssetPairs`. Odin lagrar både
Krakens kanoniska tillgångs-ID och den användarvänliga symbolen, till exempel
`XXBT`/`XBT` som `BTC`. Endast aktiva EUR-spotpar kan läggas till i allowlisten.
Utbud, status, minimibelopp och precision kan ändras när Kraken uppdaterar sin
metadata.

Globala gränser gäller över alla aktiverade par. Valfria gränser per par kan vara
ännu lägre; den mest restriktiva gränsen vinner alltid. Frontendens parväljare
kommer uteslutande från backendens sparade allowlist.

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
