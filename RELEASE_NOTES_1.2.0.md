# Project Odin 1.2.0

Odin now presents one complete interface to every user. Market Scanner, Strategy
Lab, technical values, detailed metrics, diagnostics, market data, risk settings,
and advanced controls are always available with understandable Swedish labels and
explanations.

Legacy browser preferences for the former interface selector are ignored and
removed when practical. Older configuration and API payloads containing the
retired field continue to be tolerated.

This interface change does not alter trading logic, recommendations, strategy
calculations, risk limits, or live-trading behavior. Live trading remains disabled
by default. Risk acceptance, an explicit activation phrase, a fresh server-side
preview, manual order confirmation, and the global emergency stop remain required.

## Live Kraken account and multi-asset support

Livekonto is a read-only dashboard for normalized non-zero balances, available and
reserved amounts, explicitly estimated EUR values, allocation, open orders, recent
completed/cancelled orders, fills, and fees. Unknown and unpriced assets remain
visible.

Kraken `AssetPairs` is the source of truth for active EUR spot pairs, canonical and
display symbols, order minimums, cost minimums, precision, and status. Metadata is
cached for one hour and can be refreshed manually. The selectable allowlist starts
with BTC/EUR and ETH/EUR when Kraken reports them and may be expanded to any active
EUR spot pair returned by Kraken.

Global risk limits apply across every enabled pair. Optional per-pair limits can
further restrict order amount, daily amount, and daily count; the most restrictive
limit always wins. Preview requests accept only a currently allowed backend pair
and never submit an order automatically.

## Verification status

- 56 backend tests and 6 frontend tests pass.
- Ruff, TypeScript, Prettier, production build, PyInstaller, Electron Builder,
  packaged Credential Manager self-test, and `git diff --check` pass.
- Read-only Kraken validation discovered 535 currently tradable EUR spot pairs.
- The configured account exposed the non-zero asset type `EUR`; no balances or
  private values were logged. No unsupported or unpriced asset type was present.
- Validate-only previews passed for BTC/EUR and ETH/EUR. No submission method was
  called.
- The packaged backend loaded the existing database and Credential Manager data
  and returned the live account with estimated-value marking.

Installer and portable UI interaction must still be completed in a normal
interactive Windows desktop session. The automation session could not retain the
Electron window, so this build is not declared a completed v1.2.0 release yet.

Artifacts:

- `Project-Odin-Setup-1.2.0-x64.exe` — SHA-256
  `C9938021684C62AAF816918CF046718985DBBB71F19DDC7DE3209798191FE7CE`
- `Project-Odin-Portable-1.2.0-x64.exe` — SHA-256
  `D8EB86AF82B96031C8ACA90EB559FBD04CBCBE68C39D08C90F771F29EFA149D9`
