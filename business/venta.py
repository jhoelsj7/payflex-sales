"""Capa de negocio: objeto de dominio Venta (multi-línea), base del patrón Decorator."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from data.database import Product


class VentaComponent(ABC):
    """Interfaz común entre Venta y sus decoradores (patrón Decorator)."""

    @abstractmethod
    def calcular_total(self) -> float:
        """Calcula el monto total de la venta."""


@dataclass
class VentaItem:
    """Una línea de la venta: un producto y la cantidad vendida."""

    producto: Product
    cantidad: int

    @property
    def subtotal(self) -> float:
        """Subtotal de esta línea (precio de lista, sin descuento)."""
        return self.producto.price * self.cantidad


@dataclass
class Venta(VentaComponent):
    """Representa una venta con una o más líneas de producto (carrito).

    `monto_final` permite que una Strategy de descuento (discount_strategies.py)
    fije el subtotal ya descontado sobre el conjunto de líneas; si no se fija,
    `calcular_total()` cae a la suma de precios de lista. Los decoradores de
    sale_decorators.py operan sobre este valor sin modificar esta clase.
    """

    items: list[VentaItem]
    descripcion_estrategia: str = "Sin descuento"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    monto_final: float | None = None

    def calcular_total(self) -> float:
        """Retorna el monto ya calculado por una Strategy, o la suma de líneas."""
        if self.monto_final is not None:
            return self.monto_final
        return sum(item.subtotal for item in self.items)
