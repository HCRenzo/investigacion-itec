"""Domain errors. Controllers never build HTTP errors by hand; the app maps these centrally."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class UnauthorizedError(DomainError):
    status_code = 401


class ForbiddenError(DomainError):
    status_code = 403


class ProductNotFoundError(NotFoundError):
    def __init__(self, key):
        super().__init__(f"Producto no encontrado: {key}")


class InsufficientStockError(ConflictError):
    def __init__(self, name: str):
        super().__init__(f"Stock insuficiente para {name}")
