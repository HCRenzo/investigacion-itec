from decimal import Decimal

from api.config import Settings
from api.services.receipt.base import ReceiptEngine
from api.services.receipt.fast import FastReceiptEngine
from api.services.receipt.legacy import LegacyReceiptEngine


class ReceiptEngineFactory:
    """Chooses the engine from configuration. Callers never see which one they got."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def create(self, name: str | None = None, tax_rate: Decimal | None = None) -> ReceiptEngine:
        name = (name or self.settings.receipt_engine or "v2").lower()
        tax_rate = self.settings.tax_rate if tax_rate is None else tax_rate
        if name == "v1":
            return LegacyReceiptEngine(tax_rate, self.settings.legacy_work_factor, self.settings.legacy_target_seconds)
        if name == "v2":
            return FastReceiptEngine(tax_rate)
        raise ValueError(f"Motor de recibo desconocido: {name!r} (use 'v1' o 'v2')")
