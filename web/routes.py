"""Capa de presentación web: rutas Flask con autenticación por sesión."""
import sys, os, functools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session, jsonify, abort)
from facade.sales_facade import SalesFacade
from data.database import DatabaseManager

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
        db = DatabaseManager()
        user = db.get_user(username)
        if user and user.check_password(password):
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
    recent     = list(reversed(report['transacciones']))[:5]
    customers  = DatabaseManager().get_all_customers()
    chart_labels = [f"#{i+1}" for i in range(len(report['transacciones']))]
    chart_data   = [tx['total'] for tx in report['transacciones']]
    return render_template('index.html',
        products=products, report=report, low_stock=low_stock,
        recent=recent, customers=customers,
        active_strategy=_active_strategy_desc,
        strategy_labels=STRATEGY_LABELS,
        chart_labels=chart_labels, chart_data=chart_data)


# ── Productos ─────────────────────────────────────────────

@app.route('/products')
@login_required
def products():
    return render_template('products.html', products=_facade.get_available_products())


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
            **kwargs)
        flash(f'Producto "{request.form["name"]}" registrado correctamente.', 'success')
    except ValueError as e:
        flash(str(e), 'error')
    return redirect(url_for('products'))


# ── Ventas ────────────────────────────────────────────────

@app.route('/sales', methods=['GET'])
@login_required
def sales():
    return render_template('sales.html',
        products=_facade.get_available_products(),
        strategy_labels=STRATEGY_LABELS,
        active_key=_active_strategy_key,
        active_strategy=_active_strategy_desc,
        result=None, error=None)


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
            request.form['product_id'], int(request.form['quantity']))
    except ValueError as e:
        error = str(e)
    return render_template('sales.html',
        products=_facade.get_available_products(),
        strategy_labels=STRATEGY_LABELS,
        active_key=_active_strategy_key,
        active_strategy=_active_strategy_desc,
        result=result, error=error)


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
    all_customers = DatabaseManager().get_all_customers()
    return render_template('customers.html', customers=all_customers)


@app.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    try:
        DatabaseManager().save_customer({
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


# ── Reportes ──────────────────────────────────────────────

@app.route('/reports')
@login_required
def reports():
    report = _facade.get_sales_report()
    transactions  = list(reversed(report['transacciones']))
    chart_labels  = [f"#{i+1}" for i in range(len(report['transacciones']))]
    chart_data    = [tx['total'] for tx in report['transacciones']]
    return render_template('reports.html',
        report=report, transactions=transactions,
        chart_labels=chart_labels, chart_data=chart_data)


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
