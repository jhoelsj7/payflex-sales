"""Capa de negocio: decoradores de Venta (patrón Decorator).

Extienden `calcular_total()` de forma dinámica (impuestos, descuentos
puntuales, logging) sin tocar la clase base `Venta` ni sus subclases.
Se combinan por composición y pueden apilarse en cualquier orden.
"""
from abc import abstractmethod

from business.venta import VentaComponent


class VentaDecorator(VentaComponent):
    """Decorador base: envuelve un VentaComponent y delega en él."""

    def __init__(self, venta: VentaComponent):
        """Guarda el componente envuelto (Venta u otro decorador)."""
        self._venta = venta

    @abstractmethod
    def calcular_total(self) -> float:
        """Las subclases concretas definen cómo modifican el total delegado."""


class DescuentoDecorator(VentaDecorator):
    """Aplica un descuento porcentual adicional sobre el total envuelto."""

    def __init__(self, venta: VentaComponent, porcentaje: float):
        """Inicializa con el componente a decorar y el porcentaje a descontar.

        Raises:
            ValueError: si porcentaje no está en [0, 100].
        """
        super().__init__(venta)
        if not (0 <= porcentaje <= 100):
            raise ValueError(f"Porcentaje inválido: {porcentaje}")
        self._porcentaje = porcentaje

    def calcular_total(self) -> float:
        """Retorna el total envuelto reducido en el porcentaje configurado."""
        return self._venta.calcular_total() * (1 - self._porcentaje / 100)


class ImpuestoDecorator(VentaDecorator):
    """Agrega IGV (18% por defecto) al total envuelto."""

    def __init__(self, venta: VentaComponent, porcentaje: float = 18.0):
        """Inicializa con el componente a decorar y el porcentaje de impuesto."""
        super().__init__(venta)
        self._porcentaje = porcentaje

    def calcular_total(self) -> float:
        """Retorna el total envuelto incrementado en el porcentaje de impuesto."""
        return self._venta.calcular_total() * (1 + self._porcentaje / 100)


class RegistroLogDecorator(VentaDecorator):
    """Registra en consola el total calculado, sin alterar su valor."""

    def calcular_total(self) -> float:
        """Calcula el total delegado, lo imprime como log y lo retorna sin cambios."""
        total = self._venta.calcular_total()
        print(f"  [LOG] Total de venta calculado: S/ {total:.2f}")
        return total


if __name__ == '__main__':
    from data.database import Product

    producto_demo = Product(product_id='P001', name='Audífonos', price=100.0,
                            stock=10, category='electronic')
    from business.venta import Venta

    venta = Venta(producto=producto_demo, cantidad=2)  # 200.00 base
    venta_final = ImpuestoDecorator(RegistroLogDecorator(DescuentoDecorator(venta, 10)))
    print(f"Total final (10% dscto + log + IGV 18%): S/ {venta_final.calcular_total():.2f}")
