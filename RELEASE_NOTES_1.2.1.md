# Project Odin 1.2.1

Livekonto now includes a compact searchable multi-select for backend-approved
active Kraken EUR spot pairs. Existing selections are preserved, BTC/EUR and
ETH/EUR are the reset defaults, and selected pairs appear as removable chips.

The new **Manuellt köp** card supports market and limit buys entered either as EUR
or cryptocurrency quantity. It never presents a direct purchase button. A
server-side preview validates the allowlist, live mode, emergency stop, balance,
Kraken minimums and precision, global/per-pair limits, cooldown, loss limit, and
current risk settings.

Market previews include configurable slippage, an estimated execution range, and
an explicit non-guaranteed-cost warning. Limit prices and cryptocurrency
quantities with invalid precision are rejected rather than rounded. Changing an
input removes the preview; confirmation also rejects expired previews, changed
risk settings, disabled live mode, emergency stop, or price movement beyond the
selected tolerance.

Every final purchase still requires the existing live activation safeguards and
the separate **Bekräfta riktigt köp** action. Automated tests never submit an
order.
