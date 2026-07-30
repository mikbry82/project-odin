# Project Odin 1.1.1

Project Odin 1.1.1 is a Windows credential-storage hotfix for the manually
confirmed Kraken trading foundation.

The application now requires the native Windows Credential Manager backend,
performs a random non-secret write/read/delete capability test, verifies deletion,
and rejects fallback or plaintext keyring backends. Kraken credentials use the
stable service `Project Odin / Kraken` with accounts `api_key` and `api_secret`.
Saving is verified and both entries are removed if either write fails.

The connection view includes **Testa säker lagring**. This localhost-only check
never uses or returns Kraken credentials. Diagnostic logs contain only the failure
category, exception class, backend class, packaged status, Windows version, and
backend availability.

Release artifacts:

- `Project-Odin-Setup-1.1.1-x64.exe`
- `Project-Odin-Portable-1.1.1-x64.exe`

Release acceptance requires the packaged backend self-test to complete a real
Windows Credential Manager roundtrip and confirm deletion. A build whose self-test
fails must not be published as a completed release.
