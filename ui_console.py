"""Capa de presentación: menú interactivo por consola."""
from facade.sales_facade import SalesFacade


class ConsoleUI:
    """Interfaz de usuario por consola. Solo invoca métodos de SalesFacade."""

    _TYPE_MAP = {'1': 'electronic', '2': 'clothing', '3': 'food'}
    _COMPROBANTE_MAP = {'1': 'boleta', '2': 'factura'}
    _PAGO_MAP = {'1': 'efectivo', '2': 'tarjeta', '3': 'transferencia', '4': 'pasarela'}

    def __init__(self, facade: SalesFacade):
        """Recibe la fachada como única dependencia."""
        self._facade = facade
        self._user = None

    def run(self) -> None:
        """Pide login y luego inicia el bucle principal del menú."""
        if not self._login():
            return
        actions = {
            '1': self._register_product,
            '2': self._process_sale,
            '3': self._change_strategy,
            '4': self._show_stock,
            '5': self._show_history,
            '6': self._undo_last_sale,
            '7': self._edit_product,
            '8': self._delete_product,
            '9': self._show_notifications,
        }
        while True:
            self._print_menu()
            choice = input("\nOpcion: ").strip()
            if choice == '0':
                print("\nCerrando sistema... Hasta luego!")
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Opcion no valida. Intente de nuevo.")

    # ── Autenticación (RF07) ──────────────────────────────────

    def _login(self) -> bool:
        """Solicita usuario y contraseña hasta 3 intentos. Retorna True si accedió."""
        print("=== INICIAR SESION — PayFlex Sales ===")
        for _ in range(3):
            username = input("Usuario: ").strip()
            password = input("Contrasena: ").strip()
            user = self._facade.authenticate(username, password)
            if user:
                self._user = user
                print(f"\nBienvenido, {user.full_name} ({user.role}).")
                return True
            print("Usuario o contrasena incorrectos.\n")
        print("Demasiados intentos fallidos. Cerrando.")
        return False

    # ── Menú ────────────────────────────────────────────────

    def _print_menu(self) -> None:
        """Imprime el menú principal."""
        print("\n=== SISTEMA DE GESTION DE VENTAS ===")
        print(f"Usuario: {self._user.full_name} ({self._user.role})")
        print("1. Registrar producto")
        print("2. Procesar venta (carrito)")
        print("3. Cambiar estrategia de descuento")
        print("4. Consultar stock")
        print("5. Ver historial de ventas")
        print("6. Deshacer ultima venta")
        print("7. Modificar producto")
        print("8. Eliminar producto")
        if self._user.role == 'admin':
            print("9. Ver notificaciones (admin)")
        print("0. Salir")

    # ── Productos (RF01) ──────────────────────────────────────

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
            description = input("Descripcion: ").strip()
            price = float(input("Precio (S/): "))
            stock = int(input("Stock inicial: "))
            kwargs = self._collect_extra_attrs(product_type)
            self._facade.create_product(product_type, product_id, name, price, stock,
                                        description=description, **kwargs)
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

    def _edit_product(self) -> None:
        """Modifica un producto existente (RF01)."""
        print("\n--- MODIFICAR PRODUCTO ---")
        product_id = input("ID del producto a modificar: ").strip()
        existing = self._facade.get_product(product_id)
        if existing is None:
            print("Producto no encontrado.")
            return
        print("Deje en blanco para mantener el valor actual.")
        name = input(f"Nombre [{existing.name}]: ").strip() or existing.name
        description = input(f"Descripcion [{existing.description}]: ").strip() or existing.description
        price_in = input(f"Precio [{existing.price}]: ").strip()
        stock_in = input(f"Stock [{existing.stock}]: ").strip()
        try:
            price = float(price_in) if price_in else existing.price
            stock = int(stock_in) if stock_in else existing.stock
            self._facade.update_product(product_id, name, price, stock, existing.category, description)
            print("Producto actualizado correctamente.")
        except ValueError as e:
            print(f"Error: {e}")

    def _delete_product(self) -> None:
        """Elimina un producto del catálogo (RF01)."""
        print("\n--- ELIMINAR PRODUCTO ---")
        product_id = input("ID del producto a eliminar: ").strip()
        if input(f"Confirma eliminar '{product_id}'? (s/n): ").strip().lower() != 's':
            print("Cancelado.")
            return
        try:
            self._facade.delete_product(product_id)
            print("Producto eliminado.")
        except ValueError as e:
            print(f"Error: {e}")

    # ── Venta (carrito multi-producto, RF02) ──────────────────

    def _process_sale(self) -> None:
        """Arma un carrito multi-producto, emite comprobante y cobra."""
        print("\n--- PROCESAR VENTA (CARRITO) ---")
        carrito = []
        while True:
            product_id = input("ID del producto (vacio para terminar): ").strip()
            if not product_id:
                break
            try:
                quantity = int(input("Cantidad: "))
            except ValueError:
                print("Cantidad invalida.")
                continue
            carrito.append({'product_id': product_id, 'quantity': quantity})
            print(f"  Agregado. Items en el carrito: {len(carrito)}")
        if not carrito:
            print("Carrito vacio, venta cancelada.")
            return

        print("Tipo de comprobante: (1) Boleta  (2) Factura")
        tipo = self._COMPROBANTE_MAP.get(input("Tipo: ").strip(), 'boleta')
        cliente_ruc = ''
        if tipo == 'factura':
            cliente_ruc = input("RUC del cliente (obligatorio para factura): ").strip()
        cliente_nombre = input("Nombre del cliente (opcional): ").strip()

        print("Metodo de pago: (1) Efectivo  (2) Tarjeta  (3) Transferencia  (4) Pasarela externa")
        metodo = self._PAGO_MAP.get(input("Metodo: ").strip(), 'efectivo')

        try:
            result = self._facade.process_sale(carrito, tipo, metodo, cliente_ruc, cliente_nombre)
            print(f"\n  Comprobante : {result['numero_comprobante']} ({result['tipo_comprobante'].upper()})")
            for item in result['lineas']:
                print(f"    {item['quantity']}x {item['product']} — S/ {item['unit_price']:.2f} c/u")
            print(f"  Estrategia  : {result['strategy']}")
            print(f"  Subtotal    : S/ {result['subtotal']:.2f}")
            print(f"  IGV         : S/ {result['igv']:.2f}")
            print(f"  TOTAL       : S/ {result['total']:.2f}")
            print(f"  Metodo pago : {result['metodo_pago']}")
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
        """Lista productos con filtro opcional por nombre/categoría (RF05)."""
        print("\n--- STOCK DISPONIBLE ---")
        nombre = input("Filtrar por nombre (enter para omitir): ").strip() or None
        categoria = input("Filtrar por categoria (electronic/clothing/food, enter omite): ").strip() or None
        products = self._facade.get_available_products(nombre, categoria)
        if not products:
            print("No hay productos que coincidan.")
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
            print("Venta revertida: stock restaurado y comprobante eliminado.")
        else:
            print("No hay ventas registradas para deshacer.")

    def _show_history(self) -> None:
        """Muestra el historial de ventas con filtros opcionales (RF06)."""
        print("\n--- HISTORIAL DE VENTAS ---")
        fecha_desde = input("Fecha desde (YYYY-MM-DD, enter omite): ").strip() or None
        fecha_hasta = input("Fecha hasta (YYYY-MM-DD, enter omite): ").strip() or None
        product_id = input("ID de producto (enter omite): ").strip() or None
        total_min_in = input("Total minimo (enter omite): ").strip()
        total_min = float(total_min_in) if total_min_in else None

        report = self._facade.get_sales_report(fecha_desde, fecha_hasta, product_id, total_min)
        ventas = report['ventas']
        if not ventas:
            print("No hay ventas que coincidan.")
            return
        for i, v in enumerate(ventas, 1):
            items_desc = ', '.join(f"{it['quantity']}x {it['product_name']}" for it in v['lineas'])
            print(
                f"  {i:>2}. [{v['timestamp'][:19]}] {v['numero_comprobante']} "
                f"({v['tipo_comprobante']}) {items_desc} — S/ {v['total']:.2f}"
            )
        print(f"\n  Total acumulado : S/ {report['total_ventas']:.2f}")
        print(f"  Transacciones   : {report['cantidad_transacciones']}")

    def _show_notifications(self) -> None:
        """Muestra las alertas de stock bajo (solo administrador, RF09)."""
        if self._user.role != 'admin':
            print("Solo el administrador puede ver las notificaciones.")
            return
        print("\n--- NOTIFICACIONES (ADMIN) ---")
        notifications = self._facade.get_notifications()
        if not notifications:
            print("Sin notificaciones.")
            return
        for n in notifications:
            estado = "leida" if n['leida'] else "NUEVA"
            print(f"  [{estado}] {n['timestamp'][:19]} — {n['mensaje']}")


if __name__ == '__main__':
    ConsoleUI(SalesFacade()).run()
