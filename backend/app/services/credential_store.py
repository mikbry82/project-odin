import logging
import platform
import secrets
import sys
import uuid
from dataclasses import dataclass
from enum import StrEnum

from app.exchanges.base import Credentials

SERVICE_NAME = "Project Odin / Kraken"
API_KEY_ACCOUNT = "api_key"
API_SECRET_ACCOUNT = "api_secret"
CAPABILITY_SERVICE = "Project Odin / Credential Store Capability"
logger = logging.getLogger("odin.credential_store")


class CredentialStoreErrorCategory(StrEnum):
    UNAVAILABLE = "credential_manager_unavailable"
    PACKAGING_SUPPORT_MISSING = "packaged_keyring_support_missing"
    ACCESS_DENIED = "credential_manager_access_denied"
    WRITE_FAILED = "credential_write_failed"
    VERIFICATION_FAILED = "credential_verification_failed"
    DELETE_FAILED = "credential_deletion_failed"
    UNSAFE_BACKEND = "unsafe_keyring_backend"


class CredentialStoreError(RuntimeError):
    def __init__(
        self,
        category: CredentialStoreErrorCategory,
        *,
        operation: str,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(category.value)
        self.category = category
        self.operation = operation
        self.cause_class = f"{type(cause).__module__}.{type(cause).__name__}" if cause else None


@dataclass(frozen=True)
class CredentialStoreCapability:
    available: bool
    backend_class: str
    category: CredentialStoreErrorCategory | None = None
    exception_class: str | None = None
    temporary_credential_deleted: bool = False


def _exception_category(exc: Exception, operation: str) -> CredentialStoreErrorCategory:
    winerror = getattr(exc, "winerror", None)
    if winerror in {5, 1314}:
        return CredentialStoreErrorCategory.ACCESS_DENIED
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return CredentialStoreErrorCategory.PACKAGING_SUPPORT_MISSING
    if operation == "delete":
        return CredentialStoreErrorCategory.DELETE_FAILED
    if operation == "write":
        return CredentialStoreErrorCategory.WRITE_FAILED
    return CredentialStoreErrorCategory.UNAVAILABLE


def _backend_class(backend: object) -> str:
    return f"{type(backend).__module__}.{type(backend).__name__}"


def _log_failure(
    category: CredentialStoreErrorCategory,
    *,
    operation: str,
    backend_class: str,
    exc: Exception | None,
) -> None:
    logger.error(
        "Credential store failure category=%s operation=%s exception_class=%s "
        "backend_class=%s packaged=%s windows_version=%s backend_available=false",
        category.value,
        operation,
        f"{type(exc).__module__}.{type(exc).__name__}" if exc else "none",
        backend_class,
        bool(getattr(sys, "frozen", False)),
        platform.version(),
    )


@dataclass
class CredentialStore:
    _capability: CredentialStoreCapability | None = None

    def _keyring(self):
        try:
            import keyring
        except ImportError as exc:
            raise CredentialStoreError(
                CredentialStoreErrorCategory.PACKAGING_SUPPORT_MISSING,
                operation="backend",
                cause=exc,
            ) from exc
        return keyring

    def _backend(self):
        keyring = self._keyring()
        try:
            backend = keyring.get_keyring()
        except Exception as exc:
            raise CredentialStoreError(
                _exception_category(exc, "backend"),
                operation="backend",
                cause=exc,
            ) from exc
        backend_class = _backend_class(backend)
        if backend_class != "keyring.backends.Windows.WinVaultKeyring":
            category = CredentialStoreErrorCategory.UNSAFE_BACKEND
            _log_failure(
                category,
                operation="backend",
                backend_class=backend_class,
                exc=None,
            )
            raise CredentialStoreError(category, operation="backend")
        return keyring, backend_class

    def capability(self, *, refresh: bool = False) -> CredentialStoreCapability:
        if self._capability is not None and not refresh:
            return self._capability
        try:
            keyring, backend_class = self._backend()
        except CredentialStoreError as exc:
            backend_class = "unavailable"
            _log_failure(
                exc.category,
                operation=exc.operation,
                backend_class=backend_class,
                exc=None,
            )
            self._capability = CredentialStoreCapability(
                False, backend_class, exc.category, exc.cause_class, False
            )
            return self._capability

        account = f"roundtrip_{uuid.uuid4().hex}"
        value = secrets.token_urlsafe(32)
        operation = "write"
        deleted = False
        try:
            keyring.set_password(CAPABILITY_SERVICE, account, value)
            operation = "read"
            stored = keyring.get_password(CAPABILITY_SERVICE, account)
            if not secrets.compare_digest(stored or "", value):
                raise CredentialStoreError(
                    CredentialStoreErrorCategory.VERIFICATION_FAILED,
                    operation="verify",
                )
            operation = "delete"
            keyring.delete_password(CAPABILITY_SERVICE, account)
            operation = "verify_delete"
            if keyring.get_password(CAPABILITY_SERVICE, account) is not None:
                raise CredentialStoreError(
                    CredentialStoreErrorCategory.VERIFICATION_FAILED,
                    operation="verify_delete",
                )
            deleted = True
        except CredentialStoreError as exc:
            category = exc.category
            cause = None
        except Exception as exc:
            category = _exception_category(exc, operation)
            cause = exc
        else:
            self._capability = CredentialStoreCapability(
                True,
                backend_class,
                temporary_credential_deleted=True,
            )
            logger.info(
                "Credential store capability backend_class=%s packaged=%s "
                "windows_version=%s backend_available=true",
                backend_class,
                bool(getattr(sys, "frozen", False)),
                platform.version(),
            )
            return self._capability
        finally:
            if not deleted:
                try:
                    keyring.delete_password(CAPABILITY_SERVICE, account)
                except keyring.errors.PasswordDeleteError:
                    # The failed write may not have created a credential.
                    deleted = False
                except Exception as cleanup_exc:
                    _log_failure(
                        CredentialStoreErrorCategory.DELETE_FAILED,
                        operation="capability_cleanup",
                        backend_class=backend_class,
                        exc=cleanup_exc,
                    )
                try:
                    deleted = keyring.get_password(CAPABILITY_SERVICE, account) is None
                except Exception as cleanup_verify_exc:
                    _log_failure(
                        CredentialStoreErrorCategory.DELETE_FAILED,
                        operation="capability_cleanup_verify",
                        backend_class=backend_class,
                        exc=cleanup_verify_exc,
                    )

        _log_failure(
            category,
            operation="capability",
            backend_class=backend_class,
            exc=cause,
        )
        self._capability = CredentialStoreCapability(
            False,
            backend_class,
            category,
            (f"{type(cause).__module__}.{type(cause).__name__}" if cause else None),
            deleted,
        )
        return self._capability

    def _require_available(self) -> None:
        capability = self.capability()
        if not capability.available:
            raise CredentialStoreError(
                capability.category or CredentialStoreErrorCategory.UNAVAILABLE,
                operation="capability",
            )

    def _cleanup(self, keyring) -> None:
        first_error: Exception | None = None
        for account in (API_KEY_ACCOUNT, API_SECRET_ACCOUNT):
            try:
                keyring.delete_password(SERVICE_NAME, account)
            except keyring.errors.PasswordDeleteError:
                continue
            except Exception as exc:
                first_error = first_error or exc
        if first_error:
            raise CredentialStoreError(
                _exception_category(first_error, "delete"),
                operation="delete",
                cause=first_error,
            ) from first_error

    def save(self, credentials: Credentials) -> None:
        self._require_available()
        keyring = self._keyring()
        try:
            keyring.set_password(SERVICE_NAME, API_KEY_ACCOUNT, credentials.api_key)
            keyring.set_password(SERVICE_NAME, API_SECRET_ACCOUNT, credentials.api_secret)
            stored_key = keyring.get_password(SERVICE_NAME, API_KEY_ACCOUNT)
            stored_secret = keyring.get_password(SERVICE_NAME, API_SECRET_ACCOUNT)
            if not (
                secrets.compare_digest(stored_key or "", credentials.api_key)
                and secrets.compare_digest(stored_secret or "", credentials.api_secret)
            ):
                raise CredentialStoreError(
                    CredentialStoreErrorCategory.VERIFICATION_FAILED,
                    operation="verify",
                )
        except CredentialStoreError:
            self._cleanup(keyring)
            raise
        except Exception as exc:
            try:
                self._cleanup(keyring)
            except CredentialStoreError as cleanup_exc:
                _log_failure(
                    cleanup_exc.category,
                    operation="save_cleanup",
                    backend_class=(
                        self._capability.backend_class if self._capability else "unavailable"
                    ),
                    exc=None,
                )
            category = _exception_category(exc, "write")
            _log_failure(
                category,
                operation="save",
                backend_class=(
                    self._capability.backend_class if self._capability else "unavailable"
                ),
                exc=exc,
            )
            raise CredentialStoreError(category, operation="save", cause=exc) from exc

    def load(self) -> Credentials | None:
        self._require_available()
        keyring = self._keyring()
        try:
            api_key = keyring.get_password(SERVICE_NAME, API_KEY_ACCOUNT)
            api_secret = keyring.get_password(SERVICE_NAME, API_SECRET_ACCOUNT)
        except Exception as exc:
            raise CredentialStoreError(
                _exception_category(exc, "read"),
                operation="read",
                cause=exc,
            ) from exc
        if not api_key or not api_secret:
            return None
        return Credentials(api_key=api_key, api_secret=api_secret)

    def delete(self) -> None:
        self._require_available()
        keyring = self._keyring()
        self._cleanup(keyring)


credential_store = CredentialStore()
