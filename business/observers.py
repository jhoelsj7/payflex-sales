"""Capa de negocio: observadores de ventas (patrón Observer)."""
from abc import ABC, abstractmethod
from datetime import datetime

from business.venta import Venta
from data.database import DatabaseManager


class IObservador(ABC):
    """Interfaz para observadores del ciclo de venta."""

    @abstractmethod
    def update(self, venta: Venta) -> None:
        """Recibe notificación con la venta ya procesada."""


class InventoryObserver(IObservador):
    """Actúa como gestor de inventario: descuenta stock de cada línea vendida."""

    def update(self, venta: Venta) -> None:
        """Reduce el stock de cada producto de la venta y persiste el cambio."""
        for item in venta.items:
            producto = item.producto
            producto.stock -= item.cantidad
            DatabaseManager().save_product(producto)


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
        resumen = ', '.join(f"{i.cantidad}x '{i.producto.name}'" for i in venta.items)
        print(f"  [Venta] {resumen} — S/ {total:.2f}")


class AdminNotificationObserver(IObservador):
    """Persiste una alerta para el administrador cuando el stock queda bajo.

    Se agrega como un observador más, sin modificar SaleManager ni los
    observadores existentes (Open/Closed): consulta el stock ya actualizado
    directamente en la base de datos, por lo que no depende del orden en que
    se suscriban los observadores.
    """

    UMBRAL_STOCK_BAJO = 5

    def update(self, venta: Venta) -> None:
        """Revisa cada línea vendida y notifica si el producto quedó con stock bajo."""
        db = DatabaseManager()
        for item in venta.items:
            producto_actual = db.get_product(item.producto.product_id)
            if producto_actual and producto_actual.stock < self.UMBRAL_STOCK_BAJO:
                mensaje = (f"Stock bajo: '{producto_actual.name}' "
                          f"quedan {producto_actual.stock} unidades")
                db.save_notification(mensaje, tipo='stock_bajo',
                                     timestamp=datetime.now().isoformat())
                print(f"  [ALERTA ADMIN] {mensaje}")


class EmailObserver(IObservador):
    """Stub de notificación por email tras cada venta (extensión sin modificar SaleManager)."""

    def update(self, venta: Venta) -> None:
        """Simula el envío de email de confirmación."""
        total = venta.calcular_total()
        print(f"  [Email] Confirmacion enviada: venta por S/ {total:.2f}")
