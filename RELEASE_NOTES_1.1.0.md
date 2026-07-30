# Project Odin 1.1.0 release notes

Project Odin 1.1.0 adds a disabled-by-default foundation for manually confirmed
Kraken spot trading. It does not enable unattended trading, automatic live strategy
execution, or AI-triggered orders. Existing simulation behavior and strategy
calculations are unchanged.

Safety controls include OS keyring credential storage, restrictive permission
guidance, typed live-mode activation, conservative backend limits, a persistent kill
switch, 30-second single-use previews, explicit Swedish real-money confirmation,
atomic duplicate prevention, audit transitions, and timeout reconciliation without
blind retries.

Read [LIVE_TRADING_SECURITY.md](LIVE_TRADING_SECURITY.md) before connecting Kraken.
Use only **Query Funds** and **Create & modify orders**. Never enable
**Withdraw Funds**.

Automated tests use mocks and do not submit or validate any live Kraken order.
Project Odin live trading must not be considered safe or complete until the user
performs the documented controlled validation with a restricted Kraken key and
verifies order cancellation and uncertain-result reconciliation.

Windows artifacts:

- `Project-Odin-Setup-1.1.0-x64.exe`  
  SHA-256:
  `EE2353FF5B125CC459582A096565BAE5F85C3B7341D0CDE5A204104FFA57F3B6`
- `Project-Odin-Portable-1.1.0-x64.exe`  
  SHA-256:
  `EA16C44E32561DBD5A05B99C859539644F7D9EA4164ABBA4E534DDEB81B751D1`
