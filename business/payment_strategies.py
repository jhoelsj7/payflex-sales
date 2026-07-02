"""Capa de negocio: métodos de pago intercambiables (patrón Strategy).

Complementa a payment_adapter.py: IMetodoPago es la misma interfaz que usa
PaymentAdapter (Adapter) para envolver una pasarela externa. Aquí se agregan
las estrategias "nativas" del sistema, intercambiables en tiempo de ejecución
sin que SalesFacade conozca los detalles de cada una.
"""
from business.payment_adapter import IMetodoPago


class EfectivoPago(IMetodoPago):
    """Pago en efectivo: se confirma de inmediato en caja."""

    def pagar(self, monto: float) -> bool:
        print(f"  [Efectivo] Cobrado S/ {monto:.2f} en caja.")
        return True


class TarjetaPago(IMetodoPago):
    """Pago con tarjeta (débito/crédito) vía POS."""

    def pagar(self, monto: float) -> bool:
        print(f"  [Tarjeta] Cobro de S/ {monto:.2f} aprobado por el POS.")
        return True


class TransferenciaPago(IMetodoPago):
    """Pago por transferencia o depósito bancario."""

    def pagar(self, monto: float) -> bool:
        print(f"  [Transferencia] Se registró la orden de pago de S/ {monto:.2f}.")
        return True


if __name__ == '__main__':
    for metodo in (EfectivoPago(), TarjetaPago(), TransferenciaPago()):
        metodo.pagar(100.0)
