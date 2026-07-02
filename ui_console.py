"""Capa de presentación: menú interactivo por consola."""
from facade.sales_facade import SalesFacade


class ConsoleUI:
    """Interfaz de usuario por consola. Solo invoca métodos de SalesFacade."""

    _TYPE_MAP = {'1': 'electronic', '2': 'clothing', '3': 'food'}

    def __init__(self, facade: SalesFacade):
        """Recibe la fachada como única dependencia."""
        self._facade = facade

    def run(self) -> None:
        """Inicia el bucle principal del menú hasta que el usuario elige Salir."""
        actions = {
            '1': self._register_product,
            '2': self._process_sale,
            '3': self._change_strategy,
            '4': self._show_stock,
            '5': self._show_history,
            '6': self._undo_last_sale,
        }
        while True:
            self._print_menu()
            choice = input("\nOpcion: ").strip()
            if choice == '7':
                print("\nCerrando sistema... Hasta luego!")
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Opcion no valida. Intente de nuevo.")

    # ── Menú ────────────────────────────────────────────────

    def _print_menu(self) -> None:
        """Imprime el menú principal."""
        print("\n=== SISTEMA DE GESTION DE VENTAS ===")
        print("1. Registrar producto")
        print("2. Procesar venta")
        print("3. Cambiar estrategia de descuento")
        print("4. Consultar stock")
        print("5. Ver historial de ventas")
        print("6. Deshacer ultima venta")
        print("7. Salir")

    # ── Opciones ────────────────────────────────────────────

    def _register_product(self) -> None:
        """Solicita datos y registra un nuevo producto mediante la fachada."""
        print("\n--- REGISTRAR PRODUCTO ---")
        print("Tipo: (1) Electronico  (2) Ropa  (3) Alimento")
        t = input("Tipo: ").strip()
        product_type = self._TYPE_MAP.get(t)
        if not product_type:
            print("Tipo no valido.")
            return
        try:
            product_id = input("ID del producto: ").strip()
            name = input("Nombre: ").strip()
            price = float(input("Precio (S/): "))
            stock = int(input("Stock inicial: "))
            kwargs = self._collect_extra_attrs(product_type)
            self._facade.create_product(product_type, product_id, name, price, stock, **kwargs)
            print(f"Producto '{name}' registrado correctamente.")
        except ValueError as e:
            print(f"Error: {e}")

    def _collect_extra_attrs(self, product_type: str) -> dict:
        """Solicita atributos adicionales según el tipo de producto."""
        if product_type == 'electronic':
            months = input("Meses de garantia [12]: ").strip()
            return {'warranty_months': int(months) if months else 12}
        if product_type == 'clothing':
            size = input("Talla (XS/S/M/L/XL) [M]: ").strip() or 'M'
            material = input("Material [algodon]: ").strip() or 'algodon'
            return {'size': size, 'material': material}
        if product_type == 'food':
            expiry = input("Fecha de vencimiento (YYYY-MM-DD): ").strip()
            return {'expiry_date': expiry}
        return {}

    def _process_sale(self) -> None:
        """Solicita ID y cantidad, procesa la venta e imprime el detalle."""
        print("\n--- PROCESAR VENTA ---")
        try:
            product_id = input("ID del producto: ").strip()
            quantity = int(input("Cantidad: "))
            result = self._facade.process_sale(product_id, quantity)
            print(f"\n  Producto   : {result['product']}")
            print(f"  Cantidad   : {result['quantity']}")
            print(f"  Precio u.  : S/ {result['unit_price']:.2f}")
            print(f"  Estrategia : {result['strategy']}")
            print(f"  TOTAL      : S/ {result['total']:.2f}")
        except ValueError as e:
            print(f"Error: {e}")

    def _change_strategy(self) -> None:
        """Muestra submenu y activa la estrategia de descuento elegida."""
        print("\n--- ESTRATEGIA DE DESCUENTO ---")
        print("1. Sin descuento")
        print("2. Descuento 10%")
        print("3. Cliente VIP (20% + 5% volumen)")
        print("4. Temporada (15%)")
        key = input("Seleccione estrategia: ").strip()
        try:
            desc = self._facade.set_discount_strategy(key)
            print(f"Estrategia activa: {desc}")
        except ValueError as e:
            print(f"Error: {e}")

    def _show_stock(self) -> None:
        """Lista todos los productos con su precio y stock actual."""
        print("\n--- STOCK DISPONIBLE ---")
        products = self._facade.get_available_products()
        if not products:
            print("No hay productos registrados.")
            return
        header = f"{'ID':<12} {'Nombre':<25} {'Precio':>10} {'Stock':>7} {'Categoria':<12}"
        print(header)
        print("-" * len(header))
        for p in products:
            print(
                f"{p.product_id:<12} {p.name:<25}"
                f" S/ {p.price:>8.2f} {p.stock:>7} {p.category:<12}"
            )

    def _undo_last_sale(self) -> None:
        """Revierte la última venta procesada (patrón Command)."""
        print("\n--- DESHACER ULTIMA VENTA ---")
        if self._facade.deshacer_ultima_venta():
            print("Venta revertida: stock restaurado y transaccion eliminada.")
        else:
            print("No hay ventas registradas para deshacer.")

    def _show_history(self) -> None:
        """Muestra el historial de transacciones y el total acumulado."""
        print("\n--- HISTORIAL DE VENTAS ---")
        report = self._facade.get_sales_report()
        transactions = report['transacciones']
        if not transactions:
            print("No hay ventas registradas.")
            return
        for i, tx in enumerate(transactions, 1):
            ts = tx['timestamp'][:19]
            print(
                f"  {i:>2}. [{ts}] {tx['product_name']} x{tx['quantity']}"
                f" — S/ {tx['total']:.2f} ({tx['strategy']})"
            )
        print(f"\n  Total acumulado : S/ {report['total_ventas']:.2f}")
        print(f"  Transacciones   : {report['cantidad_transacciones']}")
