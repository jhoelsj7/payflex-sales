"""Capa de negocio: objeto de dominio Venta, base del patrón Decorator."""
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
class Venta(VentaComponent):
    """Representa una venta concreta. Es el componente base a decorar.

    `monto_final` permite que una Strategy de descuento (discount_strategies.py)
    fije el subtotal ya descontado; si no se fija, `calcular_total()` cae al
    precio de lista. Los decoradores de sale_decorators.py operan sobre este
    valor sin modificar esta clase (Open/Closed).
    """

    producto: Product
    cantidad: int
    descripcion_estrategia: str = "Sin descuento"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    monto_final: float | None = None

    def calcular_total(self) -> float:
        """Retorna el monto ya calculado por una Strategy, o precio * cantidad."""
        if self.monto_final is not None:
            return self.monto_final
        return self.producto.price * self.cantidad
