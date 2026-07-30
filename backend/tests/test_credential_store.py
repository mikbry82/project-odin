import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.exchanges.base import (
    Credentials,
    CredentialStatus,
    CredentialValidation,
)
from app.services.credential_store import (
    API_KEY_ACCOUNT,
    API_SECRET_ACCOUNT,
    CAPABILITY_SERVICE,
    SERVICE_NAME,
    CredentialStore,
    CredentialStoreCapability,
    CredentialStoreError,
    CredentialStoreErrorCategory,
)


class FakePasswordDeleteError(Exception):
    pass


class FakeErrors:
    PasswordDeleteError = FakePasswordDeleteError


class FakeKeyring:
    errors = FakeErrors

    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}
        self.fail_write_account: str | None = None
        self.fail_delete_account: str | None = None

    def set_password(self, service: str, account: str, value: str) -> None:
        if account == self.fail_write_account:
            raise PermissionError("sanitized test failure")
        self.values[(service, account)] = value

    def get_password(self, service: str, account: str) -> str | None:
        return self.values.get((service, account))

    def delete_password(self, service: str, account: str) -> None:
        if account == self.fail_delete_account:
            raise PermissionError("sanitized test failure")
        if (service, account) not in self.values:
            raise FakePasswordDeleteError
        del self.values[(service, account)]


def configured_store(fake: FakeKeyring) -> CredentialStore:
    store = CredentialStore()
    store._backend = lambda: (  # type: ignore[method-assign]
        fake,
        "keyring.backends.Windows.WinVaultKeyring",
    )
    store._keyring = lambda: fake  # type: ignore[method-assign]
    return store


def test_functional_backend_capability_round_trip() -> None:
    fake = FakeKeyring()
    capability = configured_store(fake).capability(refresh=True)
    assert capability.available is True
    assert capability.backend_class == "keyring.backends.Windows.WinVaultKeyring"
    assert not any(service == CAPABILITY_SERVICE for service, _ in fake.values)


def test_write_read_delete_round_trip() -> None:
    fake = FakeKeyring()
    store = configured_store(fake)
    expected = Credentials("example-key", "example-secret")
    store.save(expected)
    assert store.load() == expected
    store.delete()
    assert store.load() is None


def test_partial_write_is_cleaned_up() -> None:
    fake = FakeKeyring()
    store = configured_store(fake)
    assert store.capability(refresh=True).available
    fake.fail_write_account = API_SECRET_ACCOUNT
    with pytest.raises(CredentialStoreError):
        store.save(Credentials("must-not-remain", "must-not-remain-either"))
    assert (SERVICE_NAME, API_KEY_ACCOUNT) not in fake.values
    assert (SERVICE_NAME, API_SECRET_ACCOUNT) not in fake.values


def test_replacement_of_existing_credentials() -> None:
    fake = FakeKeyring()
    store = configured_store(fake)
    store.save(Credentials("old-key", "old-secret"))
    replacement = Credentials("new-key", "new-secret")
    store.save(replacement)
    assert store.load() == replacement


def test_delete_when_one_credential_is_missing() -> None:
    fake = FakeKeyring()
    store = configured_store(fake)
    store.capability(refresh=True)
    fake.values[(SERVICE_NAME, API_KEY_ACCOUNT)] = "key-only"
    store.delete()
    assert not any(service == SERVICE_NAME for service, _ in fake.values)


def test_unavailable_backend() -> None:
    store = CredentialStore()

    def unavailable():
        raise CredentialStoreError(
            CredentialStoreErrorCategory.UNAVAILABLE,
            operation="backend",
        )

    store._backend = unavailable  # type: ignore[method-assign]
    capability = store.capability(refresh=True)
    assert capability.available is False
    assert capability.category is CredentialStoreErrorCategory.UNAVAILABLE


@pytest.mark.parametrize(
    "module,name",
    [
        ("keyring.backends.fail", "Keyring"),
        ("keyring.backends.null", "Keyring"),
        ("keyrings.alt.file", "PlaintextKeyring"),
    ],
)
def test_fail_null_and_plaintext_backends_are_rejected(module: str, name: str) -> None:
    backend_type = type(name, (), {"__module__": module})
    backend = backend_type()

    class KeyringModule:
        @staticmethod
        def get_keyring():
            return backend

    store = CredentialStore()
    store._keyring = lambda: KeyringModule  # type: ignore[method-assign]
    with pytest.raises(CredentialStoreError) as caught:
        store._backend()
    assert caught.value.category is CredentialStoreErrorCategory.UNSAFE_BACKEND


def test_logs_never_contain_test_secret(caplog) -> None:
    fake = FakeKeyring()
    store = configured_store(fake)
    store.capability(refresh=True)
    fake.fail_write_account = API_SECRET_ACCOUNT
    secret = "SECRET-MUST-NOT-APPEAR"
    with caplog.at_level(logging.ERROR), pytest.raises(CredentialStoreError):
        store.save(Credentials(secret, secret))
    assert secret not in caplog.text
    assert "PermissionError" in caplog.text
    assert "credential_write_failed" in caplog.text


@patch(
    "app.api.routes.live_trading.provider.validate_credentials",
    new_callable=AsyncMock,
)
@patch("app.api.routes.live_trading.credential_store.save")
def test_sanitized_api_error_contains_no_secret(
    mock_save, mock_validate: AsyncMock, api_client
) -> None:
    mock_validate.return_value = CredentialValidation(
        CredentialStatus.CONNECTED,
        account_access=True,
        order_access=None,
        withdrawal_access_absent=None,
    )
    mock_save.side_effect = CredentialStoreError(
        CredentialStoreErrorCategory.WRITE_FAILED,
        operation="save",
        cause=PermissionError("internal detail"),
    )
    response = api_client.post(
        "/api/v1/live/credentials",
        json={
            "api_key": "SECRET-API-KEY",
            "api_secret": "SECRET-PRIVATE-KEY-VALUE",
        },
    )
    assert response.status_code == 503
    body = response.text
    assert "SECRET-API-KEY" not in body
    assert "SECRET-PRIVATE-KEY-VALUE" not in body
    assert "internal detail" not in body
    assert "Windows Autentiseringshanterare" in body


def test_capability_result_can_represent_packaged_failure() -> None:
    result = CredentialStoreCapability(
        available=False,
        backend_class="unavailable",
        category=CredentialStoreErrorCategory.PACKAGING_SUPPORT_MISSING,
    )
    assert result.available is False
