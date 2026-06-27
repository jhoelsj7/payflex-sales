"""Capa de negocio: observadores de ventas (patrón Observer)."""
from abc import ABC, abstractmethod

from data.database import DatabaseManager


class SaleObserver(ABC):
    """Interfaz para observadores del ciclo de venta."""

    @abstractmethod
    def update(self, product, quantity: int, total: float) -> None:
        """Recibe notificación tras procesar una venta."""


class InventoryObserver(SaleObserver):
    """Descuenta stock y emite alerta cuando el inventario es bajo."""

    def update(self, product, quantity: int, total: float) -> None:
        """Reduce el stock del producto y persiste el cambio."""
        product.stock -= quantity
        DatabaseManager().save_product(product)
        if product.stock < 5:
            print(
                f"  [ALERTA] Stock bajo para '{product.name}'"
                f" — quedan {product.stock} unidades"
            )


class ReportObserver(SaleObserver):
    """Acumula el total de ventas e imprime resumen por transacción."""

    def __init__(self):
        """Inicializa el acumulador de ventas en cero."""
        self._total_sales: float = 0.0

    def get_total_sales(self) -> float:
        """Retorna el total acumulado de todas las ventas registradas."""
        return self._total_sales

    def update(self, product, quantity: int, total: float) -> None:
        """Acumula el total y muestra resumen de la transacción."""
        self._total_sales += total
        print(
            f"  [Venta] {quantity}x '{product.name}'"
            f" — S/ {total:.2f}"
        )


class EmailObserver(SaleObserver):
    """Stub de notificación por email tras cada venta (extensión sin modificar SaleManager)."""

    def update(self, product, quantity: int, total: float) -> None:
        """Simula el envío de email de confirmación."""
        print(
            f"  [Email] Confirmacion enviada: {quantity}x '{product.name}'"
            f" por S/ {total:.2f}"
        )
