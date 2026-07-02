"""Capa de negocio: adaptación de pasarela de pago externa (patrón Adapter)."""
from abc import ABC, abstractmethod


class IMetodoPago(ABC):
    """Interfaz de métodos de pago que SalesFacade/SaleManager conocen."""

    @abstractmethod
    def pagar(self, monto: float) -> bool:
        """Procesa el cobro de `monto`. Retorna True si el pago fue aprobado."""


class PasarelaPagoExterna:
    """Pasarela de pago de un proveedor externo (firma incompatible).

    Simula un SDK de terceros que no podemos ni debemos modificar:
    usa `realizar_cobro(cantidad, moneda)` en vez de `pagar(monto)`.
    """

    def realizar_cobro(self, cantidad: float, moneda: str = 'PEN') -> dict:
        """Cobra `cantidad` en `moneda` y retorna la respuesta cruda del proveedor."""
        print(f"  [PasarelaExterna] Cobrando {cantidad:.2f} {moneda}...")
        return {'estado': 'aprobado', 'monto_cobrado': cantidad, 'moneda': moneda}


class PaymentAdapter(IMetodoPago):
    """Adapta PasarelaPagoExterna a la interfaz IMetodoPago del sistema.

    Permite que SaleManager/SalesFacade cobren usando `pagar(monto)` sin
    conocer ni modificar la API real de la pasarela externa.
    """

    def __init__(self, pasarela: PasarelaPagoExterna | None = None, moneda: str = 'PEN'):
        """Inicializa el adaptador con una pasarela externa y su moneda."""
        self._pasarela = pasarela or PasarelaPagoExterna()
        self._moneda = moneda

    def pagar(self, monto: float) -> bool:
        """Traduce la llamada del sistema a la firma de la pasarela externa."""
        respuesta = self._pasarela.realizar_cobro(monto, self._moneda)
        return respuesta.get('estado') == 'aprobado'


if __name__ == '__main__':
    metodo: IMetodoPago = PaymentAdapter()
    resultado = metodo.pagar(150.0)
    print("Pago exitoso" if resultado else "Pago rechazado")
