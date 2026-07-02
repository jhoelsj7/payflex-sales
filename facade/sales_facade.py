"""Capa fachada: interfaz unificada hacia la capa de presentación (patrón Facade)."""
from business.discount_strategies import (
    NoDiscountStrategy,
    PercentageDiscountStrategy,
    SeasonalDiscountStrategy,
    VIPClientStrategy,
)
from business.observers import InventoryObserver, ReportObserver
from business.payment_adapter import IMetodoPago, PaymentAdapter
from business.sale_commands import HistorialComandos, RegistrarVentaCommand
from business.sale_manager import SaleManager
from data.database import DatabaseManager
from data.product_factory import (
    ClothingProductFactory,
    ElectronicProductFactory,
    FoodProductFactory,
)


class SalesFacade:
    """Fachada que simplifica el acceso a los subsistemas de ventas.

    Oculta la inicialización y coordinación de DatabaseManager, SaleManager,
    observadores, estrategias, fábricas, el adaptador de pago (Adapter) y el
    historial de comandos reversibles (Command).
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
        self._metodo_pago: IMetodoPago = PaymentAdapter()
        self._historial = HistorialComandos()

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

    def process_sale(self, product_id: str, quantity: int, incluir_igv: bool = False) -> dict:
        """Procesa la venta de un producto vía Command y cobra vía Adapter.

        La venta se encapsula en un RegistrarVentaCommand (patrón Command) y se
        ejecuta a través de HistorialComandos, lo que permite revertirla luego
        con deshacer_ultima_venta(). El cobro se delega a IMetodoPago (patrón
        Adapter); si la pasarela lo rechaza, la venta se deshace automáticamente.

        Returns:
            dict con claves: product, quantity, unit_price, total, strategy.

        Raises:
            ValueError: si el producto no existe, el stock es insuficiente o el pago es rechazado.
        """
        product = self._db.get_product(product_id)
        if product is None:
            raise ValueError(f"Producto '{product_id}' no encontrado.")
        if product.stock < quantity:
            raise ValueError(
                f"Stock insuficiente. Disponible: {product.stock}, solicitado: {quantity}."
            )
        comando = RegistrarVentaCommand(self._sale_manager, product, quantity, incluir_igv)
        self._historial.ejecutar(comando)

        if not self._metodo_pago.pagar(comando.total):
            self._historial.deshacer_ultimo()
            raise ValueError("El pago fue rechazado por la pasarela de pago.")

        return {
            'product': product.name,
            'quantity': quantity,
            'unit_price': product.price,
            'total': comando.total,
            'strategy': self._sale_manager.get_strategy_description(),
        }

    def deshacer_ultima_venta(self) -> bool:
        """Revierte la última venta procesada (stock y transacción). Patrón Command."""
        return self._historial.deshacer_ultimo()

    def get_sales_report(self) -> dict:
        """Retorna reporte consolidado calculado desde la base de datos.

        Se calcula desde las transacciones persistidas (no desde el acumulador
        en memoria de ReportObserver) para que quede consistente con ventas
        deshechas mediante deshacer_ultima_venta().
        """
        transacciones = self._db.get_transactions()
        return {
            'total_ventas': sum(tx['total'] for tx in transacciones),
            'cantidad_transacciones': len(transacciones),
            'transacciones': transacciones,
        }
