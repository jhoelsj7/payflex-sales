"""Capa de negocio: comandos de venta reversibles (patrón Command)."""
from abc import ABC, abstractmethod

from business.comprobante_factory import Comprobante, ComprobanteFactory
from business.payment_adapter import IMetodoPago
from business.sale_manager import SaleManager
from business.venta import Venta
from data.database import DatabaseManager, Product


class Command(ABC):
    """Interfaz de comando: toda acción encapsulada sabe ejecutarse y deshacerse."""

    @abstractmethod
    def execute(self) -> None:
        """Ejecuta la acción encapsulada."""

    @abstractmethod
    def undo(self) -> None:
        """Revierte la acción previamente ejecutada."""


class RegistrarVentaCommand(Command):
    """Encapsula el registro de una venta (con una o más líneas) y permite revertirla.

    Al ejecutar: aplica descuento y notifica observadores vía SaleManager
    (descuenta stock), emite el comprobante (Factory Method) y cobra vía
    IMetodoPago (Strategy o Adapter); solo si el cobro es aceptado persiste
    la venta completa en la base de datos.
    Al deshacer: restaura el stock de cada línea y elimina la venta persistida.
    """

    def __init__(self, sale_manager: SaleManager, comprobante_factory: ComprobanteFactory,
                items: list[tuple[Product, int]], metodo_pago: IMetodoPago,
                cliente_ruc: str = '', cliente_nombre: str = ''):
        """Guarda los datos necesarios para ejecutar y, luego, poder deshacer la venta."""
        self._sale_manager = sale_manager
        self._comprobante_factory = comprobante_factory
        self._items = items
        self._metodo_pago = metodo_pago
        self._cliente_ruc = cliente_ruc
        self._cliente_nombre = cliente_nombre
        self.subtotal: float | None = None
        self.comprobante: Comprobante | None = None
        self.total: float | None = None
        self._venta: Venta | None = None
        self._venta_id: int | None = None
        self._ejecutado = False

    def execute(self) -> None:
        """Aplica descuento, notifica observadores, cobra y persiste la venta.

        SaleManager.process_sale ya descuenta stock (vía InventoryObserver)
        antes de que se conozca si el comprobante es válido o el pago se
        acepta. Por eso, cualquier fallo posterior (RUC faltante, pago
        rechazado) restaura el stock antes de propagar la excepción.

        Raises:
            ValueError: RUC faltante en factura o pago rechazado (la venta
                no queda persistida y el stock queda intacto).
        """
        self.subtotal = self._sale_manager.process_sale(self._items)
        self._venta = self._sale_manager.get_last_venta()

        try:
            self.comprobante = self._comprobante_factory.crear_comprobante(
                self.subtotal, self._cliente_ruc, self._cliente_nombre)
            self.total = self.comprobante.total
            if not self._metodo_pago.pagar(self.total):
                raise ValueError("El pago fue rechazado por el método seleccionado.")
        except ValueError:
            self._restaurar_stock()
            raise

        venta_data = {
            'numero_comprobante': self.comprobante.numero,
            'tipo_comprobante': self.comprobante.tipo,
            'cliente_ruc': self.comprobante.cliente_ruc,
            'cliente_nombre': self.comprobante.cliente_nombre,
            'metodo_pago': type(self._metodo_pago).__name__,
            'estrategia_descuento': self._venta.descripcion_estrategia,
            'subtotal': self.subtotal,
            'igv': self.comprobante.calcular_igv(),
            'total': self.total,
            'timestamp': self._venta.timestamp,
        }
        items_data = [{
            'product_id': vi.producto.product_id, 'product_name': vi.producto.name,
            'quantity': vi.cantidad, 'unit_price': vi.producto.price,
            'line_total': vi.subtotal,
        } for vi in self._venta.items]
        self._venta_id = DatabaseManager().save_venta(venta_data, items_data)
        self._ejecutado = True

    def undo(self) -> None:
        """Restaura el stock de cada línea y elimina la venta persistida por execute()."""
        if not self._ejecutado:
            return
        self._restaurar_stock()
        if self._venta_id is not None:
            DatabaseManager().delete_venta(self._venta_id)
        self._ejecutado = False
        print(f"  [Deshacer] Venta {self.comprobante.numero} revertida (stock restaurado).")

    def _restaurar_stock(self) -> None:
        """Devuelve al inventario la cantidad de cada línea de la venta."""
        for item in self._venta.items:
            item.producto.stock += item.cantidad
            DatabaseManager().save_product(item.producto)


class HistorialComandos:
    """Invoker: ejecuta comandos y mantiene un historial para deshacer el último."""

    def __init__(self):
        """Inicializa el historial vacío."""
        self._historial: list[Command] = []

    def ejecutar(self, comando: Command) -> None:
        """Ejecuta el comando y, si no lanza excepción, lo apila en el historial."""
        comando.execute()
        self._historial.append(comando)

    def deshacer_ultimo(self) -> bool:
        """Deshace el último comando ejecutado. Retorna False si no hay historial."""
        if not self._historial:
            return False
        self._historial.pop().undo()
        return True
