"""Capa de negocio: comandos de venta reversibles (patrón Command)."""
from abc import ABC, abstractmethod

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
    """Encapsula el registro de una venta y permite revertirla.

    Al deshacer: restaura el stock del producto y elimina la transacción
    persistida por SaleManager.process_sale, dejando el sistema como si
    la venta nunca se hubiera realizado.
    """

    def __init__(self, sale_manager: SaleManager, producto: Product,
                cantidad: int, incluir_igv: bool = False):
        """Guarda los datos necesarios para ejecutar y, luego, poder deshacer la venta."""
        self._sale_manager = sale_manager
        self._producto = producto
        self._cantidad = cantidad
        self._incluir_igv = incluir_igv
        self.total: float | None = None
        self._venta: Venta | None = None
        self._ejecutado = False

    def execute(self) -> None:
        """Registra la venta a través de SaleManager y guarda su resultado."""
        self.total = self._sale_manager.process_sale(
            self._producto, self._cantidad, self._incluir_igv)
        self._venta = self._sale_manager.get_last_venta()
        self._ejecutado = True

    def undo(self) -> None:
        """Restaura el stock y elimina la transacción registrada por execute()."""
        if not self._ejecutado:
            return
        self._producto.stock += self._cantidad
        DatabaseManager().save_product(self._producto)
        if self._venta is not None:
            DatabaseManager().delete_transaction(
                self._venta.producto.product_id, self._venta.timestamp)
        self._ejecutado = False
        print(f"  [Deshacer] Venta de {self._cantidad}x "
              f"'{self._producto.name}' revertida (stock restaurado).")


class HistorialComandos:
    """Invoker: ejecuta comandos y mantiene un historial para deshacer el último."""

    def __init__(self):
        """Inicializa el historial vacío."""
        self._historial: list[Command] = []

    def ejecutar(self, comando: Command) -> None:
        """Ejecuta el comando y lo apila en el historial."""
        comando.execute()
        self._historial.append(comando)

    def deshacer_ultimo(self) -> bool:
        """Deshace el último comando ejecutado. Retorna False si no hay historial."""
        if not self._historial:
            return False
        self._historial.pop().undo()
        return True
