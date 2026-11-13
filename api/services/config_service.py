from api.config import Settings
from api.repositories.order import ParameterRepository

ENGINE_KEY = "MOTOR_RECIBO"
MODES = ("auto", "v1", "v2")


class ConfigService:
    """Which receipt engine is active. Precedence:
    1. t_parametro.MOTOR_RECIBO when the admin panel set it to v1 or v2 (applies to every deployment sharing the DB),
    2. the RECEIPT_ENGINE environment variable of this deployment (mode 'auto'),
    3. v2.
    """

    def __init__(self, params: ParameterRepository, settings: Settings):
        self.params = params
        self.settings = settings

    def stored_mode(self) -> str:
        value = (self.params.value(ENGINE_KEY) or "auto").lower()
        return value if value in MODES else "auto"

    def active_engine(self) -> tuple[str, str]:
        """(engine, where it came from)."""
        mode = self.stored_mode()
        if mode in ("v1", "v2"):
            return mode, "panel de administración"
        if self.settings.receipt_engine:
            return self.settings.receipt_engine, "variable de entorno RECEIPT_ENGINE"
        return "v2", "valor por defecto"

    def set_mode(self, mode: str) -> None:
        self.params.set(ENGINE_KEY, mode, "Motor de calculo del recibo: v1 (lento), v2 (rapido) o auto (usa el entorno)")
        self.params.commit()

    def describe(self) -> dict:
        engine, source = self.active_engine()
        return {"receipt_engine": engine, "source": source, "mode": self.stored_mode(),
                "env_engine": self.settings.receipt_engine,
                "legacy_work_factor": self.settings.legacy_work_factor if engine == "v1" else None}
