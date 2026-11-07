from api.config import Settings
from api.services.receipt.base import ReceiptEngine
from api.services.receipt.fast import FastReceiptEngine
from api.services.receipt.legacy import LegacyReceiptEngine


class ReceiptEngineFactory:
    """Chooses the engine from configuration. Callers never see which one they got."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def create(self, name: str | None = None) -> ReceiptEngine:
        name = (name or self.settings.receipt_engine).lower()
        if name == "v1":
            return LegacyReceiptEngine(self.settings.tax_rate, self.settings.legacy_work_factor)
        if name == "v2":
            return FastReceiptEngine(self.settings.tax_rate)
        raise ValueError(f"Motor de recibo desconocido: {name!r} (use 'v1' o 'v2')")
