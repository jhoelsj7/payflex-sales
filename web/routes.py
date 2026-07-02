"""Capa de presentación web: rutas Flask con autenticación por sesión.

Toda la lógica pasa por SalesFacade — esta capa no importa DatabaseManager
ni ningún otro módulo interno directamente (patrón Facade).
"""
import sys, os, functools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session, jsonify, abort)
from facade.sales_facade import SalesFacade

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'payflex-sales-secret-2026'

_facade = SalesFacade()
_active_strategy_key = '1'
_active_strategy_desc = 'Sin descuento'

STRATEGY_LABELS = {
    '1': 'Sin descuento',
    '2': 'Descuento 10%',
    '3': 'Cliente VIP (20% + 5% volumen)',
    '4': 'Temporada (15%)',
}

COMPROBANTE_LABELS = {'boleta': 'Boleta', 'factura': 'Factura'}
PAGO_LABELS = {
    'efectivo': 'Efectivo (Strategy)',
    'tarjeta': 'Tarjeta (Strategy)',
    'transferencia': 'Transferencia (Strategy)',
    'pasarela': 'Pasarela externa (Adapter)',
}

ROLE_LABELS = {'admin': 'Administrador', 'vendedor': 'Vendedor', 'supervisor': 'Supervisor'}
ROLE_COLORS = {'admin': '#4f46e5', 'vendedor': '#059669', 'supervisor': '#d97706'}


# ── Autenticación ─────────────────────────────────────────

def login_required(f):
    """Decorator que redirige al login si no hay sesión activa."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            flash('Inicia sesión para continuar.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator que exige rol admin (403 en caso contrario)."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def current_user():
    """Retorna dict con info del usuario en sesión o None."""
    if 'username' not in session:
        return None
    return {
        'username':  session.get('username'),
        'full_name': session.get('full_name'),
        'role':      session.get('role'),
        'role_label': ROLE_LABELS.get(session.get('role', ''), ''),
        'role_color': ROLE_COLORS.get(session.get('role', ''), '#64748b'),
    }


app.jinja_env.globals['current_user'] = current_user


# ── Login / Logout ────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = _facade.authenticate(username, password)
        if user:
            session['username']  = user.username
            session['full_name'] = user.full_name
            session['role']      = user.role
            return redirect(url_for('dashboard'))
        flash('Usuario o contraseña incorrectos.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    global _active_strategy_desc
    products   = _facade.get_available_products()
    report     = _facade.get_sales_report()
    low_stock  = [p for p in products if p.stock < 5]
    recent     = list(reversed(report['ventas']))[:5]
    customers  = _facade.get_customers()
    chart_labels = [f"#{i+1}" for i in range(len(report['ventas']))]
    chart_data   = [v['total'] for v in report['ventas']]
    return render_template('index.html',
        products=products, report=report, low_stock=low_stock,
        recent=recent, customers=customers,
        active_strategy=_active_strategy_desc,
        strategy_labels=STRATEGY_LABELS,
        chart_labels=chart_labels, chart_data=chart_data)


# ── Productos (RF01, RF05) ─────────────────────────────────

@app.route('/products')
@login_required
def products():
    nombre = request.args.get('q') or None
    categoria = request.args.get('categoria') or None
    return render_template('products.html',
        products=_facade.get_available_products(nombre, categoria),
        filtro_nombre=nombre or '', filtro_categoria=categoria or '')


@app.route('/products/add', methods=['POST'])
@login_required
def add_product():
    try:
        ptype = request.form['product_type']
        kwargs = {}
        if ptype == 'electronic':
            kwargs['warranty_months'] = int(request.form.get('warranty_months', 12))
        elif ptype == 'clothing':
            kwargs['size']     = request.form.get('size', 'M')
            kwargs['material'] = request.form.get('material', 'algodón')
        elif ptype == 'food':
            kwargs['expiry_date'] = request.form.get('expiry_date', '')
        _facade.create_product(
            ptype,
            request.form['product_id'].strip(),
            request.form['name'].strip(),
            float(request.form['price']),
            int(request.form['stock']),
            description=request.form.get('description', '').strip(),
            **kwargs)
        flash(f'Producto "{request.form["name"]}" registrado correctamente.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('products'))


@app.route('/products/<product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = _facade.get_product(product_id)
    if product is None:
        flash(f"Producto '{product_id}' no encontrado.", 'error')
        return redirect(url_for('products'))
    if request.method == 'POST':
        try:
            _facade.update_product(
                product_id,
                request.form['name'].strip(),
                float(request.form['price']),
                int(request.form['stock']),
                product.category,
                description=request.form.get('description', '').strip())
            flash(f'Producto "{product_id}" actualizado.', 'success')
            return redirect(url_for('products'))
        except ValueError as e:
            flash(str(e), 'error')
    return render_template('edit_product.html', product=product)


@app.route('/products/<product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    try:
        _facade.delete_product(product_id)
        flash(f'Producto "{product_id}" eliminado.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('products'))


# ── Ventas: carrito multi-producto (RF02, RF03, RF08) ──────

@app.route('/sales', methods=['GET'])
@login_required
def sales():
    cart = session.get('cart', [])
    products = _facade.get_available_products()
    products_by_id = {p.product_id: p for p in products}
    cart_detail = [{
        'product_id': item['product_id'],
        'name': products_by_id[item['product_id']].name if item['product_id'] in products_by_id else item['product_id'],
        'quantity': item['quantity'],
        'unit_price': products_by_id[item['product_id']].price if item['product_id'] in products_by_id else 0,
    } for item in cart]
    cart_total = sum(i['unit_price'] * i['quantity'] for i in cart_detail)
    return render_template('sales.html',
        products=products, cart=cart_detail, cart_total=cart_total,
        strategy_labels=STRATEGY_LABELS, active_key=_active_strategy_key,
        active_strategy=_active_strategy_desc,
        comprobante_labels=COMPROBANTE_LABELS, pago_labels=PAGO_LABELS,
        result=None, error=None)


@app.route('/sales/cart/add', methods=['POST'])
@login_required
def cart_add():
    cart = session.get('cart', [])
    cart.append({'product_id': request.form['product_id'], 'quantity': int(request.form['quantity'])})
    session['cart'] = cart
    return redirect(url_for('sales'))


@app.route('/sales/cart/remove/<int:idx>', methods=['POST'])
@login_required
def cart_remove(idx):
    cart = session.get('cart', [])
    if 0 <= idx < len(cart):
        cart.pop(idx)
    session['cart'] = cart
    return redirect(url_for('sales'))


@app.route('/sales/cart/clear', methods=['POST'])
@login_required
def cart_clear():
    session['cart'] = []
    return redirect(url_for('sales'))


@app.route('/sales/process', methods=['POST'])
@login_required
def process_sale():
    global _active_strategy_key, _active_strategy_desc
    result = error = None
    key = request.form.get('strategy_key', '1')
    try:
        _active_strategy_desc = _facade.set_discount_strategy(key)
        _active_strategy_key  = key
    except ValueError as e:
        flash(str(e), 'error')

    try:
        result = _facade.process_sale(
            session.get('cart', []),
            tipo_comprobante=request.form.get('tipo_comprobante', 'boleta'),
            metodo_pago_key=request.form.get('metodo_pago', 'efectivo'),
            cliente_ruc=request.form.get('cliente_ruc', '').strip(),
            cliente_nombre=request.form.get('cliente_nombre', '').strip())
        session['cart'] = []
    except ValueError as e:
        error = str(e)

    products = _facade.get_available_products()
    return render_template('sales.html',
        products=products, cart=[], cart_total=0,
        strategy_labels=STRATEGY_LABELS, active_key=_active_strategy_key,
        active_strategy=_active_strategy_desc,
        comprobante_labels=COMPROBANTE_LABELS, pago_labels=PAGO_LABELS,
        result=result, error=error)


@app.route('/sales/undo', methods=['POST'])
@login_required
def undo_sale():
    if _facade.deshacer_ultima_venta():
        flash('Última venta revertida (stock restaurado, comprobante eliminado).', 'success')
    else:
        flash('No hay ventas para deshacer.', 'error')
    return redirect(url_for('sales'))


@app.route('/strategy/set', methods=['POST'])
@login_required
def set_strategy():
    global _active_strategy_key, _active_strategy_desc
    key = request.form.get('strategy_key', '1')
    try:
        _active_strategy_desc = _facade.set_discount_strategy(key)
        _active_strategy_key  = key
        flash(f'Estrategia: {_active_strategy_desc}', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(request.referrer or url_for('dashboard'))


# ── Clientes ──────────────────────────────────────────────

@app.route('/customers')
@login_required
def customers():
    return render_template('customers.html', customers=_facade.get_customers())


@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    try:
        _facade.add_customer({
            'name':     request.form['name'].strip(),
            'email':    request.form.get('email', '').strip(),
            'phone':    request.form.get('phone', '').strip(),
            'ruc':      request.form.get('ruc', '').strip(),
            'city':     request.form.get('city', '').strip(),
            'category': request.form.get('category', 'regular'),
            'notes':    request.form.get('notes', '').strip(),
        })
        flash(f'Cliente "{request.form["name"]}" agregado.', 'success')
    except Exception as e:
        flash(str(e), 'error')
    return redirect(url_for('customers'))


# ── Reportes (RF06) ─────────────────────────────────────────

@app.route('/reports')
@login_required
def reports():
    fecha_desde = request.args.get('fecha_desde') or None
    fecha_hasta = request.args.get('fecha_hasta') or None
    product_id  = request.args.get('product_id') or None
    total_min_s = request.args.get('total_min')
    total_min   = float(total_min_s) if total_min_s else None

    report = _facade.get_sales_report(fecha_desde, fecha_hasta, product_id, total_min)
    ventas = list(reversed(report['ventas']))
    chart_labels = [f"#{i+1}" for i in range(len(report['ventas']))]
    chart_data   = [v['total'] for v in report['ventas']]
    return render_template('reports.html',
        report=report, ventas=ventas,
        chart_labels=chart_labels, chart_data=chart_data,
        filtro={'fecha_desde': fecha_desde or '', 'fecha_hasta': fecha_hasta or '',
               'product_id': product_id or '', 'total_min': total_min_s or ''})


# ── Notificaciones (RF09) ───────────────────────────────────

@app.route('/notifications')
@login_required
@admin_required
def notifications():
    return render_template('notifications.html', notifications=_facade.get_notifications())


# ── API JSON ──────────────────────────────────────────────

@app.route('/api/products')
@login_required
def api_products():
    return jsonify([{'id': p.product_id, 'name': p.name,
                     'price': p.price, 'stock': p.stock,
                     'category': p.category} for p in _facade.get_available_products()])


# ── Errores ───────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('404.html', code=403,
                           msg='No tienes permiso para ver esta página.'), 403
