"""Capa de negocio: comprobantes de pago y sus fábricas (patrón Factory Method).

Boleta y Factura son subclases concretas de la clase abstracta Comprobante.
BoletaFactory/FacturaFactory son las fábricas concretas que las instancian;
la Fachada las selecciona por diccionario, sin condicionales dispersos.

Vive en la capa de negocio (no en data/) porque reutiliza ImpuestoDecorator
para el cálculo de IGV; poner aquí la fábrica evita que la capa de datos
dependa de la capa de negocio.
"""
from abc import ABC, abstractmethod
from datetime import datetime

from business.sale_decorators import ImpuestoDecorator
from business.venta import VentaComponent
from data.database import DatabaseManager


class _MontoComponent(VentaComponent):
    """Adapta un monto ya calculado al contrato VentaComponent para reutilizar
    ImpuestoDecorator también aquí, fuera del flujo de SaleManager."""

    def __init__(self, monto: float):
        self._monto = monto

    def calcular_total(self) -> float:
        return self._monto


class Comprobante(ABC):
    """Clase abstracta base de todo comprobante de pago emitido."""

    def __init__(self, numero: str, cliente_ruc: str, cliente_nombre: str, subtotal: float):
        self.numero = numero
        self.cliente_ruc = cliente_ruc
        self.cliente_nombre = cliente_nombre
        self.subtotal = subtotal
        self.timestamp = datetime.now().isoformat()

    @property
    @abstractmethod
    def tipo(self) -> str:
        """Identificador del tipo de comprobante ('boleta' | 'factura')."""

    @abstractmethod
    def calcular_igv(self) -> float:
        """Calcula el IGV a desglosar en el comprobante."""

    @property
    def total(self) -> float:
        """Monto final: subtotal más el IGV desglosado (si aplica)."""
        return self.subtotal + self.calcular_igv()


class Boleta(Comprobante):
    """El precio ya incluye impuestos: no se desglosa IGV adicional."""

    @property
    def tipo(self) -> str:
        return 'boleta'

    def calcular_igv(self) -> float:
        return 0.0


class Factura(Comprobante):
    """Exige RUC del cliente y desglosa IGV 18% reutilizando ImpuestoDecorator."""

    def __init__(self, numero: str, cliente_ruc: str, cliente_nombre: str, subtotal: float):
        if not cliente_ruc:
            raise ValueError("La factura requiere el RUC del cliente.")
        super().__init__(numero, cliente_ruc, cliente_nombre, subtotal)

    @property
    def tipo(self) -> str:
        return 'factura'

    def calcular_igv(self) -> float:
        total_con_igv = ImpuestoDecorator(_MontoComponent(self.subtotal)).calcular_total()
        return total_con_igv - self.subtotal


class ComprobanteFactory(ABC):
    """Fábrica abstracta: define el contrato para emitir un comprobante."""

    @abstractmethod
    def crear_comprobante(self, subtotal: float, cliente_ruc: str = '',
                          cliente_nombre: str = '') -> Comprobante:
        """Crea el comprobante correspondiente con numeración correlativa."""


class BoletaFactory(ComprobanteFactory):
    """Emite boletas, con RUC y nombre de cliente opcionales."""

    def crear_comprobante(self, subtotal: float, cliente_ruc: str = '',
                          cliente_nombre: str = '') -> Comprobante:
        numero = DatabaseManager().next_numero_comprobante('boleta')
        return Boleta(numero, cliente_ruc, cliente_nombre, subtotal)


class FacturaFactory(ComprobanteFactory):
    """Emite facturas; Factura valida el RUC obligatorio internamente."""

    def crear_comprobante(self, subtotal: float, cliente_ruc: str = '',
                          cliente_nombre: str = '') -> Comprobante:
        numero = DatabaseManager().next_numero_comprobante('factura')
        return Factura(numero, cliente_ruc, cliente_nombre, subtotal)
