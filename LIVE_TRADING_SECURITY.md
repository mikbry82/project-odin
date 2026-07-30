# Live trading security

Project Odin 1.1.0 contains a safety-gated foundation for manually confirmed Kraken
spot orders. It does not permit unattended or AI-triggered live trading.

## Manuella försäljningar i 1.3.0

Manuella spotförsäljningar använder samma avstängda standardläge, aktiveringskrav,
nödstopp, server-preview, korta giltighetstid och engångsbekräftelse som köp.
`buy_only` är fortsatt en backendspärr; säljorder kan inte skapas förrän användaren
uttryckligen har stängt av den begränsningen.

Säljbar mängd beräknas alltid från Krakens **tillgängliga** saldo. Reserverade medel
räknas aldrig in i procentknapparna och kan inte säljas. Backend kontrollerar saldot
igen vid bekräftelse. Om saldo, pris, riskinställningar, live-läge eller nödstopp har
ändrats krävs en ny preview.

En accepterad säljorder är inte nödvändigtvis fylld. Kontrollera öppna ordrar,
avslut och saldo efter skickad order. Limitordrar kan förbli öppna eller endast
delvis fyllas.

## Supported scope

- Kraken Spot API only
- BTC/EUR and ETH/EUR allowlist by default
- no margin, leverage, futures, staking, deposits, withdrawals, or transfers
- no automatic strategy execution

Every live order is created from a short-lived server preview and requires the user
to press **Bekräfta riktig order**. An Odin recommendation can never submit an order.

## Kraken API permissions

Create a dedicated Kraken API key with only:

- **Query Funds**
- **Create & modify orders**

Never enable **Withdraw Funds**. Project Odin does not request or use withdrawal,
deposit, transfer, staking, margin, leverage, or futures permissions. Kraken does
not expose a complete API-key permission inventory through its API, so Project Odin
warns that withdrawal-permission verification is incomplete. Verify permissions in
Kraken before connecting the key.

## Credential storage

The API key and private key are stored through the operating-system keyring. On
Windows this is Windows Credential Manager. They are not stored in SQLite, `.env`,
JSON, browser storage, frontend state, source control, or logs. Once saved, secrets
are never returned to the renderer.

Revoke a key in Kraken immediately if the computer or key may be compromised. Then
use **Ta bort nyckel** in Project Odin. Credential removal activates the persistent
kill switch and resets trading to off.

## Live-mode gates and risk limits

Simulation/test-account behavior remains unchanged and live trading is disabled by
default. Enabling manual live mode requires:

1. a connected Kraken key;
2. accepted real-money risk warning;
3. the typed phrase `JAG FÖRSTÅR RISKEN`;
4. configured order and daily-amount limits;
5. a configured daily-loss limit;
6. a separately inactive kill switch.

Conservative defaults are approximately the requested SEK limits, expressed in EUR
because the initial pairs settle in EUR:

- EUR 10 maximum per order;
- EUR 30 maximum submitted total per day;
- three confirmed orders per day;
- EUR 10 daily realized-loss limit;
- 60-second cooldown;
- BTC/EUR and ETH/EUR only;
- buy-only mode enabled.

The backend enforces every limit independently from the UI. Limits never increase
silently.

## Kill switch and cancellation

**NÖDSTOPP LIVE** is visible on every page. It immediately blocks new live previews
and confirmations, resets the mode to off, and remains active after restart.
Re-enabling requires a separate manual reset followed by all live-mode gates.

The kill switch does not cancel an existing order. **Avbryt alla öppna ordrar** is a
separate confirmed action. Filled orders cannot be cancelled.

## Duplicate prevention and uncertain outcomes

Each preview and order has unique internal, preview, and Kraken client IDs. The order
record and confirmation timestamp are committed before submission. Preview IDs are
single-use and expire after 30 seconds. A second confirmation is rejected.

Project Odin never blindly retries a timed-out submission. An uncertain result is
stored as `unknown_pending_reconciliation`; Kraken order status must be reconciled
before any retry decision. Audit records contain preview/submitted values, status
changes, timestamps, sanitized failure categories, and exchange status—but never
credentials, signatures, authentication headers, nonces, or full authenticated
payloads.

## Backup and recovery

Back up the local Project Odin database while the application is closed. Credentials
are not included because they remain in the operating-system credential store.
After restoring data on another computer, create a new restricted Kraken API key.
Any uncertain order must be compared with Kraken's order history before live mode is
used again.

## Manual validation

Automated tests use mocks and never contact order-submission endpoints. The separate
`scripts/kraken_live_smoke.py` script requires the explicit
`ODIN_KRAKEN_MANUAL_SMOKE=I_UNDERSTAND_REAL_MONEY_RISK` flag, starts read-only,
performs Kraken's validate-only preview, and requires a second typed phrase before a
real limit order.

Do not run that script without supervising Kraken directly. Project Odin live
trading must not be considered safe or complete until the user performs controlled
validation with a restricted key and confirms cancellation/reconciliation behavior.

Project Odin is not financial advice. Real-money orders can lose their entire value,
and all financial decisions and consequences remain the user's responsibility.
# Livekonto och flera spotpar i 1.2.0

## Manuell köporder i 1.2.1

Livekonto visar ingen direkt köpknapp. Marknads- och limitköp måste först skapa en
kortlivad serverpreview. Ändrat par, belopp, ordertyp, limitpris eller
slippagetolerans tar bort previewn. Backend kontrollerar dessutom riskinställningar
och aktuellt pris igen vid bekräftelsen.

Marknadspris och kostnad är aldrig garantier. Prisrörelser över vald tolerans
avvisas. Limitpris och kryptomängd med för många decimaler avvisas utan automatisk
uppåtrundning. En accepterad order kan förbli öppen eller endast delvis fylld.

Livekonto använder endast autentiserade läsoperationer för saldon, öppna/stängda
ordrar och handelshistorik. Uppdatering av sidan kan aldrig skicka en order.
Tillgångar utan direkt EUR-pris döljs inte och får inget påhittat värde.

Krakens publika `AssetPairs` är enda källa för tillgänglighet, status, minsta
orderstorlek, minsta orderkostnad och precision. Ett par måste både vara aktivt i
Kraken-metadata och finnas i backendens allowlist. Globala riskgränser summeras
över samtliga par och kombineras med valfria per-par-gränser enligt den mest
restriktiva regeln.

Manuell preview använder Krakens aktuella regler, saldo och pris men skickar ingen
order. Orderläggning kräver fortfarande liveaktivering, accepterad riskvarning, ett
nytt kortlivat preview-ID och den separata bekräftelsetexten.
