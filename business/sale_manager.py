"""Capa de negocio: sujeto del Observer y orquestador de ventas."""
from datetime import datetime

from business.discount_strategies import DiscountStrategy, NoDiscountStrategy
from business.observers import SaleObserver
from data.database import DatabaseManager


class SaleManager:
    """Orquesta el proceso de venta aplicando Strategy y notificando Observer.

    Actúa como Sujeto (Subject) del patrón Observer y como contexto
    del patrón Strategy para los algoritmos de descuento.
    """

    def __init__(self):
        """Inicializa con lista vacía de observadores y estrategia sin descuento."""
        self._observers: list[SaleObserver] = []
        self._strategy: DiscountStrategy = NoDiscountStrategy()

    def subscribe(self, observer: SaleObserver) -> None:
        """Registra un observador para recibir notificaciones de venta."""
        self._observers.append(observer)

    def unsubscribe(self, observer: SaleObserver) -> None:
        """Elimina un observador previamente registrado."""
        self._observers.remove(observer)

    def set_discount_strategy(self, strategy: DiscountStrategy) -> None:
        """Reemplaza la estrategia de descuento activa en tiempo de ejecución."""
        self._strategy = strategy

    def get_strategy_description(self) -> str:
        """Retorna la descripción de la estrategia de descuento actual."""
        return self._strategy.get_description()

    def process_sale(self, product, quantity: int) -> float:
        """Procesa la venta: calcula total, notifica observadores y persiste.

        Returns:
            Total de la venta con descuento aplicado.
        """
        total = self._strategy.calculate_discount(product.price, quantity)
        self._notify_observers(product, quantity, total)
        DatabaseManager().save_transaction({
            'product_id': product.product_id,
            'product_name': product.name,
            'quantity': quantity,
            'unit_price': product.price,
            'total': total,
            'strategy': self._strategy.get_description(),
            'timestamp': datetime.now().isoformat(),
        })
        return total

    def _notify_observers(self, product, quantity: int, total: float) -> None:
        """Notifica a todos los observadores suscritos."""
        for observer in self._observers:
            observer.update(product, quantity, total)
