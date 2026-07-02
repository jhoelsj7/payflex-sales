"""Capa de negocio: observadores de ventas (patrón Observer)."""
from abc import ABC, abstractmethod

from business.venta import Venta
from data.database import DatabaseManager


class IObservador(ABC):
    """Interfaz para observadores del ciclo de venta."""

    @abstractmethod
    def update(self, venta: Venta) -> None:
        """Recibe notificación con la venta ya procesada."""


class InventoryObserver(IObservador):
    """Actúa como gestor de inventario: descuenta stock y alerta si es bajo."""

    def update(self, venta: Venta) -> None:
        """Reduce el stock del producto vendido y persiste el cambio."""
        producto = venta.producto
        producto.stock -= venta.cantidad
        DatabaseManager().save_product(producto)
        if producto.stock < 5:
            print(
                f"  [ALERTA] Stock bajo para '{producto.name}'"
                f" — quedan {producto.stock} unidades"
            )


class ReportObserver(IObservador):
    """Acumula un total en memoria e imprime resumen por transacción.

    El reporte persistido (SalesFacade.get_sales_report) se calcula desde
    la base de datos, no desde este acumulador: este observador solo sirve
    como ejemplo de efecto secundario en tiempo real (log de consola).
    """

    def __init__(self):
        """Inicializa el acumulador de ventas en cero."""
        self._total_sales: float = 0.0

    def get_total_sales(self) -> float:
        """Retorna el total acumulado en memoria desde que arrancó el proceso."""
        return self._total_sales

    def update(self, venta: Venta) -> None:
        """Acumula el total y muestra resumen de la transacción."""
        total = venta.calcular_total()
        self._total_sales += total
        print(
            f"  [Venta] {venta.cantidad}x '{venta.producto.name}'"
            f" — S/ {total:.2f}"
        )


class EmailObserver(IObservador):
    """Stub de notificación por email tras cada venta (extensión sin modificar SaleManager)."""

    def update(self, venta: Venta) -> None:
        """Simula el envío de email de confirmación."""
        print(
            f"  [Email] Confirmacion enviada: {venta.cantidad}x '{venta.producto.name}'"
            f" por S/ {venta.calcular_total():.2f}"
        )
