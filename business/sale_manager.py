"""Capa de negocio: sujeto del Observer y orquestador de ventas."""
from business.discount_strategies import DiscountStrategy, NoDiscountStrategy
from business.observers import IObservador
from business.sale_decorators import ImpuestoDecorator, RegistroLogDecorator
from business.venta import Venta
from data.database import DatabaseManager


class SaleManager:
    """Orquesta el proceso de venta aplicando Strategy y notificando Observer.

    Actúa como Sujeto (Subject) del patrón Observer y como contexto
    del patrón Strategy para los algoritmos de descuento. El total final
    se calcula envolviendo la Venta con decoradores (patrón Decorator):
    siempre se registra un log y, opcionalmente, se agrega IGV.
    """

    def __init__(self):
        """Inicializa con lista vacía de observadores y estrategia sin descuento."""
        self._observers: list[IObservador] = []
        self._strategy: DiscountStrategy = NoDiscountStrategy()
        self._last_venta: Venta | None = None

    def subscribe(self, observer: IObservador) -> None:
        """Registra un observador para recibir notificaciones de venta."""
        self._observers.append(observer)

    def unsubscribe(self, observer: IObservador) -> None:
        """Elimina un observador previamente registrado."""
        self._observers.remove(observer)

    def set_discount_strategy(self, strategy: DiscountStrategy) -> None:
        """Reemplaza la estrategia de descuento activa en tiempo de ejecución."""
        self._strategy = strategy

    def get_strategy_description(self) -> str:
        """Retorna la descripción de la estrategia de descuento actual."""
        return self._strategy.get_description()

    def get_last_venta(self) -> Venta | None:
        """Retorna la última Venta procesada (usada por RegistrarVentaCommand para deshacer)."""
        return self._last_venta

    def process_sale(self, product, quantity: int, incluir_igv: bool = False) -> float:
        """Procesa la venta: aplica descuento, decora el total, notifica y persiste.

        Returns:
            Total de la venta (con descuento y, si se pide, IGV incluido).
        """
        subtotal = self._strategy.calculate_discount(product.price, quantity)
        venta = Venta(producto=product, cantidad=quantity,
                      descripcion_estrategia=self._strategy.get_description())
        venta.monto_final = subtotal

        componente = RegistroLogDecorator(venta)
        if incluir_igv:
            componente = ImpuestoDecorator(componente)
        total = componente.calcular_total()

        self._last_venta = venta
        self._notify_observers(venta)
        DatabaseManager().save_transaction({
            'product_id': product.product_id,
            'product_name': product.name,
            'quantity': quantity,
            'unit_price': product.price,
            'total': total,
            'strategy': self._strategy.get_description(),
            'timestamp': venta.timestamp,
        })
        return total

    def _notify_observers(self, venta: Venta) -> None:
        """Notifica a todos los observadores suscritos con la venta procesada."""
        for observer in self._observers:
            observer.update(venta)
