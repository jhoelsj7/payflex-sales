"""Capa fachada: interfaz unificada hacia la capa de presentación (patrón Facade)."""
from business.comprobante_factory import BoletaFactory, ComprobanteFactory, FacturaFactory
from business.discount_strategies import (
    NoDiscountStrategy,
    PercentageDiscountStrategy,
    SeasonalDiscountStrategy,
    VIPClientStrategy,
)
from business.observers import AdminNotificationObserver, InventoryObserver, ReportObserver
from business.payment_adapter import IMetodoPago, PaymentAdapter
from business.payment_strategies import EfectivoPago, TarjetaPago, TransferenciaPago
from business.sale_commands import HistorialComandos, RegistrarVentaCommand
from business.sale_manager import SaleManager
from data.database import DatabaseManager, Product
from data.product_factory import (
    ClothingProductFactory,
    ElectronicProductFactory,
    FoodProductFactory,
)


class SalesFacade:
    """Fachada que simplifica el acceso a los subsistemas de ventas.

    Es el único punto de entrada que debe usar la capa de presentación
    (consola o web): oculta la inicialización y coordinación de
    DatabaseManager, SaleManager, observadores, estrategias de descuento,
    fábricas de productos y comprobantes, métodos de pago y el historial
    de comandos reversibles.
    """

    def __init__(self):
        """Inicializa y conecta todos los subsistemas internos."""
        self._db = DatabaseManager()
        self._sale_manager = SaleManager()
        self._inventory_observer = InventoryObserver()
        self._report_observer = ReportObserver()
        self._admin_notification_observer = AdminNotificationObserver()
        self._sale_manager.subscribe(self._inventory_observer)
        self._sale_manager.subscribe(self._report_observer)
        self._sale_manager.subscribe(self._admin_notification_observer)

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
        self._comprobante_factories: dict[str, ComprobanteFactory] = {
            'boleta': BoletaFactory(),
            'factura': FacturaFactory(),
        }
        self._metodos_pago: dict[str, IMetodoPago] = {
            'efectivo': EfectivoPago(),
            'tarjeta': TarjetaPago(),
            'transferencia': TransferenciaPago(),
            'pasarela': PaymentAdapter(),
        }
        self._historial = HistorialComandos()

    # ── Autenticación ────────────────────────────────────────

    def authenticate(self, username: str, password: str):
        """Valida credenciales contra la BD. Retorna el usuario o None."""
        user = self._db.get_user(username)
        if user and user.check_password(password):
            return user
        return None

    # ── Clientes ─────────────────────────────────────────────

    def get_customers(self) -> list:
        """Retorna todos los clientes registrados."""
        return self._db.get_all_customers()

    def add_customer(self, data: dict) -> None:
        """Registra un nuevo cliente."""
        self._db.save_customer(data)

    # ── Gestión de productos (RF01) ────────────────────────────

    def get_available_products(self, nombre: str | None = None, categoria: str | None = None) -> list:
        """Retorna los productos disponibles, opcionalmente filtrados."""
        return self._db.get_all_products(nombre, categoria)

    def get_product(self, product_id: str) -> Product | None:
        """Retorna un producto por su ID, o None si no existe."""
        return self._db.get_product(product_id)

    def create_product(self, product_type: str, product_id: str, name: str,
                       price: float, stock: int, description: str = '', **kwargs):
        """Crea y registra un producto usando la fábrica correspondiente.

        Raises:
            ValueError: tipo inválido, precio <= 0, o ID ya registrado.
        """
        if product_type not in self._factories:
            raise ValueError(
                f"Tipo '{product_type}' no válido. Use: {list(self._factories.keys())}"
            )
        if price <= 0:
            raise ValueError("El precio debe ser mayor a cero.")
        if self._db.get_product(product_id) is not None:
            raise ValueError(
                f"Ya existe un producto con ID '{product_id}'. Use 'Modificar' para actualizar su stock."
            )
        return self._factories[product_type].register_product(
            product_id, name, price, stock, description=description, **kwargs
        )

    def update_product(self, product_id: str, name: str, price: float, stock: int,
                       category: str, description: str = '') -> Product:
        """Modifica un producto ya existente, preservando sus atributos extra.

        Raises:
            ValueError: si el producto no existe o el precio es <= 0.
        """
        existing = self._db.get_product(product_id)
        if existing is None:
            raise ValueError(f"Producto '{product_id}' no encontrado.")
        if price <= 0:
            raise ValueError("El precio debe ser mayor a cero.")
        updated = Product(product_id=product_id, name=name, price=price, stock=stock,
                          category=category, description=description,
                          extra_attrs=existing.extra_attrs)
        self._db.save_product(updated)
        return updated

    def delete_product(self, product_id: str) -> None:
        """Elimina un producto del catálogo.

        Raises:
            ValueError: si el producto no existe.
        """
        if self._db.get_product(product_id) is None:
            raise ValueError(f"Producto '{product_id}' no encontrado.")
        self._db.delete_product(product_id)

    # ── Estrategia de descuento ──────────────────────────────

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

    # ── Procesamiento de ventas (carrito multi-producto) ──────

    def process_sale(self, carrito: list[dict], tipo_comprobante: str = 'boleta',
                     metodo_pago_key: str = 'efectivo', cliente_ruc: str = '',
                     cliente_nombre: str = '') -> dict:
        """Procesa la venta de un carrito completo.

        Args:
            carrito: lista de {'product_id': str, 'quantity': int}.
            tipo_comprobante: 'boleta' o 'factura' (factura exige cliente_ruc).
            metodo_pago_key: 'efectivo' | 'tarjeta' | 'transferencia' | 'pasarela'.

        Returns:
            dict con el detalle del comprobante emitido.

        Raises:
            ValueError: carrito vacío, producto inexistente, stock insuficiente,
                tipo de comprobante o método de pago inválido, RUC faltante en
                factura, o pago rechazado.
        """
        if not carrito:
            raise ValueError("El carrito está vacío.")

        items: list[tuple[Product, int]] = []
        for linea in carrito:
            product = self._db.get_product(linea['product_id'])
            if product is None:
                raise ValueError(f"Producto '{linea['product_id']}' no encontrado.")
            cantidad = int(linea['quantity'])
            if product.stock < cantidad:
                raise ValueError(
                    f"Stock insuficiente para '{product.name}'. "
                    f"Disponible: {product.stock}, solicitado: {cantidad}."
                )
            items.append((product, cantidad))

        comprobante_factory = self._comprobante_factories.get(tipo_comprobante)
        if comprobante_factory is None:
            raise ValueError(f"Tipo de comprobante '{tipo_comprobante}' no válido.")
        metodo_pago = self._metodos_pago.get(metodo_pago_key)
        if metodo_pago is None:
            raise ValueError(f"Método de pago '{metodo_pago_key}' no válido.")

        comando = RegistrarVentaCommand(
            self._sale_manager, comprobante_factory, items,
            metodo_pago, cliente_ruc, cliente_nombre)
        self._historial.ejecutar(comando)

        return {
            'numero_comprobante': comando.comprobante.numero,
            'tipo_comprobante': comando.comprobante.tipo,
            'cliente_ruc': comando.comprobante.cliente_ruc,
            'cliente_nombre': comando.comprobante.cliente_nombre,
            'lineas': [{'product': p.name, 'quantity': q, 'unit_price': p.price} for p, q in items],
            'subtotal': comando.subtotal,
            'igv': comando.comprobante.calcular_igv(),
            'total': comando.total,
            'strategy': self._sale_manager.get_strategy_description(),
            'metodo_pago': metodo_pago_key,
        }

    def deshacer_ultima_venta(self) -> bool:
        """Revierte la última venta procesada (stock y comprobante). Patrón Command."""
        return self._historial.deshacer_ultimo()

    # ── Reportes (RF06) ───────────────────────────────────────

    def get_sales_report(self, fecha_desde: str | None = None, fecha_hasta: str | None = None,
                         product_id: str | None = None, total_min: float | None = None) -> dict:
        """Retorna el reporte consolidado de ventas, opcionalmente filtrado."""
        ventas = self._db.get_ventas(fecha_desde, fecha_hasta, product_id, total_min)
        return {
            'total_ventas': sum(v['total'] for v in ventas),
            'cantidad_transacciones': len(ventas),
            'ventas': ventas,
        }

    # ── Notificaciones (RF09) ─────────────────────────────────

    def get_notifications(self) -> list:
        """Retorna las alertas de stock bajo registradas para el administrador."""
        return self._db.get_notifications()
