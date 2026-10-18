"""Domain-level errors used across data and service layers."""


class LedgerGuardError(Exception):
    """Base error for expected LedgerGuard failures."""


class DatasetLoadError(LedgerGuardError):
    """The sponsor dataset is absent, malformed, or unsupported."""


class SchemaDriftError(DatasetLoadError):
    """A required source schema contract changed."""


class NormalizationError(LedgerGuardError):
    """A raw record cannot be mapped without guessing."""

