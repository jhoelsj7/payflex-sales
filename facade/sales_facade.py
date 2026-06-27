"""Capa fachada: interfaz unificada hacia la capa de presentación (patrón Facade)."""
from business.discount_strategies import (
    NoDiscountStrategy,
    PercentageDiscountStrategy,
    SeasonalDiscountStrategy,
    VIPClientStrategy,
)
from business.observers import InventoryObserver, ReportObserver
from business.sale_manager import SaleManager
from data.database import DatabaseManager
from data.product_factory import (
    ClothingProductFactory,
    ElectronicProductFactory,
    FoodProductFactory,
)


class SalesFacade:
    """Fachada que simplifica el acceso a los subsistemas de ventas.

    Oculta la inicialización y coordinación de DatabaseManager,
    SaleManager, observadores, estrategias y fábricas.
    """

    def __init__(self):
        """Inicializa y conecta todos los subsistemas internos."""
        self._db = DatabaseManager()
        self._sale_manager = SaleManager()
        self._inventory_observer = InventoryObserver()
        self._report_observer = ReportObserver()
        self._sale_manager.subscribe(self._inventory_observer)
        self._sale_manager.subscribe(self._report_observer)
        self._factories = {
            'electronic': ElectronicProductFactory(),
            'clothing': ClothingProductFactory(),
            'food': FoodProductFactory(),
        }
        self._discount_strategies = {
            '1': NoDiscountStrategy(),
            '2': PercentageDiscountStrategy(10),
            '3': VIPClientStrategy(),
            '4': SeasonalDiscountStrategy(),
        }

    def get_available_products(self) -> list:
        """Retorna la lista de todos los productos disponibles en inventario."""
        return self._db.get_all_products()

    def create_product(self, product_type: str, product_id: str, name: str,
                       price: float, stock: int, **kwargs):
        """Crea y registra un producto usando la fábrica correspondiente.

        Raises:
            ValueError: si product_type no es 'electronic', 'clothing' ni 'food'.
        """
        if product_type not in self._factories:
            raise ValueError(
                f"Tipo '{product_type}' no válido. Use: {list(self._factories.keys())}"
            )
        return self._factories[product_type].register_product(
            product_id, name, price, stock, **kwargs
        )

    def set_discount_strategy(self, strategy_key: str) -> str:
        """Activa la estrategia de descuento indicada y retorna su descripción.

        Raises:
            ValueError: si strategy_key no está en {'1', '2', '3', '4'}.
        """
        if strategy_key not in self._discount_strategies:
            raise ValueError(f"Estrategia '{strategy_key}' no válida.")
        strategy = self._discount_strategies[strategy_key]
        self._sale_manager.set_discount_strategy(strategy)
        return strategy.get_description()

    def process_sale(self, product_id: str, quantity: int) -> dict:
        """Procesa la venta de un producto y retorna el detalle de la transacción.

        Returns:
            dict con claves: product, quantity, unit_price, total, strategy.

        Raises:
            ValueError: si el producto no existe o el stock es insuficiente.
        """
        product = self._db.get_product(product_id)
        if product is None:
            raise ValueError(f"Producto '{product_id}' no encontrado.")
        if product.stock < quantity:
            raise ValueError(
                f"Stock insuficiente. Disponible: {product.stock}, solicitado: {quantity}."
            )
        total = self._sale_manager.process_sale(product, quantity)
        return {
            'product': product.name,
            'quantity': quantity,
            'unit_price': product.price,
            'total': total,
            'strategy': self._sale_manager.get_strategy_description(),
        }

    def get_sales_report(self) -> dict:
        """Retorna reporte consolidado: total acumulado y lista de transacciones."""
        return {
            'total_ventas': self._report_observer.get_total_sales(),
            'cantidad_transacciones': len(self._db.get_transactions()),
            'transacciones': self._db.get_transactions(),
        }
