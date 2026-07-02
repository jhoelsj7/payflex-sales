"""Capa de negocio: sujeto del Observer y orquestador de ventas."""
from business.discount_strategies import DiscountStrategy, NoDiscountStrategy
from business.observers import IObservador
from business.sale_decorators import RegistroLogDecorator
from business.venta import Venta, VentaItem
from data.database import Product


class SaleManager:
    """Orquesta el proceso de venta aplicando Strategy y notificando Observer.

    Actúa como Sujeto (Subject) del patrón Observer y como contexto del
    patrón Strategy para los algoritmos de descuento. No persiste nada en
    la base de datos: solo calcula el total y notifica a los observadores
    (que sí descuentan stock). La persistencia del comprobante queda a
    cargo de RegistrarVentaCommand, que conoce el tipo de comprobante.
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
        """Retorna la última Venta procesada (usada por RegistrarVentaCommand)."""
        return self._last_venta

    def process_sale(self, items: list[tuple[Product, int]]) -> float:
        """Procesa una venta con una o más líneas de producto (carrito).

        La estrategia de descuento activa se aplica línea por línea (mismo
        contrato `calculate_discount(precio, cantidad)` de siempre) y se
        suman los resultados. El total se decora con RegistroLogDecorator
        antes de notificar a los observadores.

        Returns:
            Subtotal de la venta con descuento aplicado (sin IGV).
        """
        venta_items = [VentaItem(producto=p, cantidad=q) for p, q in items]
        subtotal_con_descuento = sum(
            self._strategy.calculate_discount(vi.producto.price, vi.cantidad)
            for vi in venta_items
        )

        venta = Venta(items=venta_items, descripcion_estrategia=self._strategy.get_description())
        venta.monto_final = subtotal_con_descuento
        total = RegistroLogDecorator(venta).calcular_total()

        self._last_venta = venta
        self._notify_observers(venta)
        return total

    def _notify_observers(self, venta: Venta) -> None:
        """Notifica a todos los observadores suscritos con la venta procesada."""
        for observer in self._observers:
            observer.update(venta)
