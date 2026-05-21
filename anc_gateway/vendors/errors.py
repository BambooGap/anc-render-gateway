from __future__ import annotations


class VendorAdapterError(RuntimeError):
    """Base error for vendor adapter failures."""


class VendorConfigurationError(VendorAdapterError):
    """Raised when vendor configuration is missing or invalid."""


class VendorHTTPError(VendorAdapterError):
    """Raised when a vendor HTTP response is unsuccessful."""


class VendorResponseParseError(VendorAdapterError):
    """Raised when a vendor response cannot be parsed."""


class VendorTimeoutError(VendorAdapterError):
    """Raised when a vendor request times out."""


class VendorUnsupportedCapabilityError(VendorAdapterError):
    """Raised when a request requires an unsupported vendor capability."""
