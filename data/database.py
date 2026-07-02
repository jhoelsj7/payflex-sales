"""Capa de datos: Singleton DatabaseManager con SQLAlchemy + SQLite."""
import json
import os
from dataclasses import dataclass, field

from sqlalchemy import Boolean, Column, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash


# ── Modelos SQLAlchemy ────────────────────────────────────

class Base(DeclarativeBase):
    pass


class ProductModel(Base):
    __tablename__ = 'products'
    product_id  = Column(String, primary_key=True)
    name        = Column(String, nullable=False)
    description = Column(String, default='')
    price       = Column(Float,  nullable=False)
    stock       = Column(Integer, nullable=False)
    category    = Column(String, nullable=False)
    extra_attrs = Column(Text, default='{}')


class VentaModel(Base):
    """Cabecera de una venta: agrupa una o más líneas (TransactionModel)."""
    __tablename__ = 'ventas'
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    numero_comprobante  = Column(String, nullable=False, unique=True)
    tipo_comprobante    = Column(String, nullable=False)  # boleta | factura
    cliente_ruc         = Column(String, default='')
    cliente_nombre      = Column(String, default='')
    metodo_pago         = Column(String, nullable=False)
    estrategia_descuento = Column(String, nullable=False)
    subtotal            = Column(Float, nullable=False)
    igv                 = Column(Float, nullable=False, default=0.0)
    total                = Column(Float, nullable=False)
    timestamp           = Column(String, nullable=False)


class TransactionModel(Base):
    """Línea de detalle de una venta (un producto dentro de la venta)."""
    __tablename__ = 'transactions'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    venta_id     = Column(Integer, nullable=False)
    product_id   = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    quantity     = Column(Integer, nullable=False)
    unit_price   = Column(Float, nullable=False)
    line_total   = Column(Float, nullable=False)


class NotificationModel(Base):
    __tablename__ = 'notifications'
    id        = Column(Integer, primary_key=True, autoincrement=True)
    mensaje   = Column(Text, nullable=False)
    tipo      = Column(String, nullable=False, default='stock_bajo')
    leida     = Column(Boolean, nullable=False, default=False)
    timestamp = Column(String, nullable=False)


class UserModel(Base):
    __tablename__ = 'users'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    username     = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name    = Column(String, nullable=False)
    role         = Column(String, nullable=False)  # admin | vendedor | supervisor
    avatar       = Column(String, default='')

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class CustomerModel(Base):
    __tablename__ = 'customers'
    id       = Column(Integer, primary_key=True, autoincrement=True)
    name     = Column(String, nullable=False)
    email    = Column(String, default='')
    phone    = Column(String, default='')
    ruc      = Column(String, default='')
    city     = Column(String, default='')
    category = Column(String, default='regular')  # regular | vip | corporativo
    notes    = Column(Text, default='')


# ── Modelos de dominio ────────────────────────────────────

@dataclass
class Product:
    """Modelo de dominio de un producto."""
    product_id: str
    name: str
    price: float
    stock: int
    category: str
    description: str = ''
    extra_attrs: dict = field(default_factory=dict)


# ── Singleton DatabaseManager ─────────────────────────────

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sales.db')
_DB_URL  = f'sqlite:///{_DB_PATH}'

_DEFAULT_USERS = [
    {'username': 'admin',      'password': 'admin123',  'full_name': 'Administrador',       'role': 'admin'},
    {'username': 'vendedor',   'password': 'venta456',  'full_name': 'Carlos Quispe',        'role': 'vendedor'},
    {'username': 'supervisor', 'password': 'super789',  'full_name': 'María Flores',         'role': 'supervisor'},
]

_DEFAULT_CUSTOMERS = [
    {'name': 'Tech Solutions SAC',    'email': 'compras@techsol.pe',   'phone': '998-112-233', 'ruc': '20123456789', 'city': 'Lima',   'category': 'corporativo'},
    {'name': 'Distribuidora Norte',   'email': 'dnorte@gmail.com',     'phone': '944-567-890', 'ruc': '20987654321', 'city': 'Trujillo','category': 'vip'},
    {'name': 'Juan Pérez',            'email': 'jperez@outlook.com',   'phone': '912-345-678', 'ruc': '',            'city': 'Cusco',  'category': 'regular'},
    {'name': 'Inversiones Sur EIRL',  'email': 'isur@empresa.com',     'phone': '987-654-321', 'ruc': '20456789012', 'city': 'Arequipa','category': 'vip'},
    {'name': 'Minimarket El Sol',     'email': 'elsol@ventas.pe',      'phone': '923-456-789', 'ruc': '10345678901', 'city': 'Piura',  'category': 'regular'},
    {'name': 'Ana Mamani',            'email': 'amamani@hotmail.com',  'phone': '965-432-100', 'ruc': '',            'city': 'Puno',   'category': 'regular'},
    {'name': 'Corporación Andina SA', 'email': 'andina@corp.com.pe',   'phone': '01-445-6789', 'ruc': '20654321098', 'city': 'Lima',   'category': 'corporativo'},
    {'name': 'Luis Condori',          'email': 'lcondori@gmail.com',   'phone': '976-543-210', 'ruc': '',            'city': 'Tacna',  'category': 'regular'},
]


class DatabaseManager:
    """Acceso persistente a SQLite + SQLAlchemy (patrón Singleton)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            instance = super().__new__(cls)
            engine = create_engine(_DB_URL, echo=False, connect_args={'check_same_thread': False})
            Base.metadata.create_all(engine)
            instance._Session = sessionmaker(bind=engine, expire_on_commit=False)
            cls._instance = instance
            instance._seed_defaults()
        return cls._instance

    def _seed_defaults(self):
        """Inserta usuarios y clientes demo si la BD está vacía."""
        with self._Session() as s:
            if s.query(UserModel).count() == 0:
                for u in _DEFAULT_USERS:
                    s.add(UserModel(
                        username=u['username'],
                        password_hash=generate_password_hash(u['password']),
                        full_name=u['full_name'],
                        role=u['role'],
                    ))
                s.commit()
            if s.query(CustomerModel).count() == 0:
                for c in _DEFAULT_CUSTOMERS:
                    s.add(CustomerModel(**c))
                s.commit()

    # ── Productos ─────────────────────────────────────────

    def get_all_products(self, nombre: str | None = None, categoria: str | None = None) -> list:
        with self._Session() as s:
            query = s.query(ProductModel)
            if nombre:
                query = query.filter(ProductModel.name.ilike(f'%{nombre}%'))
            if categoria:
                query = query.filter(ProductModel.category == categoria)
            return [self._row_to_product(m) for m in query.all()]

    def get_product(self, product_id: str):
        with self._Session() as s:
            m = s.query(ProductModel).filter_by(product_id=product_id).first()
            return self._row_to_product(m) if m else None

    def save_product(self, product: Product) -> None:
        with self._Session() as s:
            m = s.query(ProductModel).filter_by(product_id=product.product_id).first()
            if m:
                m.name = product.name; m.price = product.price
                m.stock = product.stock; m.category = product.category
                m.description = product.description
                m.extra_attrs = json.dumps(product.extra_attrs)
            else:
                s.add(ProductModel(product_id=product.product_id, name=product.name,
                                   description=product.description,
                                   price=product.price, stock=product.stock,
                                   category=product.category,
                                   extra_attrs=json.dumps(product.extra_attrs)))
            s.commit()

    def delete_product(self, product_id: str) -> None:
        with self._Session() as s:
            m = s.query(ProductModel).filter_by(product_id=product_id).first()
            if m:
                s.delete(m)
                s.commit()

    # ── Ventas (cabecera + líneas) ─────────────────────────

    def next_numero_comprobante(self, tipo_comprobante: str) -> str:
        """Calcula el siguiente número correlativo para 'boleta' o 'factura'."""
        prefijo = 'B' if tipo_comprobante == 'boleta' else 'F'
        with self._Session() as s:
            count = s.query(VentaModel).filter_by(tipo_comprobante=tipo_comprobante).count()
            return f"{prefijo}-{count + 1:06d}"

    def save_venta(self, venta_data: dict, items: list) -> int:
        """Persiste la cabecera de la venta y sus líneas de detalle. Retorna el id de la venta."""
        with self._Session() as s:
            venta = VentaModel(**venta_data)
            s.add(venta)
            s.commit()
            s.refresh(venta)
            for item in items:
                s.add(TransactionModel(venta_id=venta.id, **item))
            s.commit()
            return venta.id

    def delete_venta(self, venta_id: int) -> None:
        """Elimina una venta completa: cabecera y todas sus líneas (usado por undo)."""
        with self._Session() as s:
            s.query(TransactionModel).filter_by(venta_id=venta_id).delete()
            s.query(VentaModel).filter_by(id=venta_id).delete()
            s.commit()

    def get_ventas(self, fecha_desde: str | None = None, fecha_hasta: str | None = None,
                  product_id: str | None = None, total_min: float | None = None) -> list:
        """Retorna las ventas (cabecera + líneas) aplicando filtros opcionales."""
        with self._Session() as s:
            query = s.query(VentaModel)
            if fecha_desde:
                query = query.filter(VentaModel.timestamp >= fecha_desde)
            if fecha_hasta:
                query = query.filter(VentaModel.timestamp <= fecha_hasta + 'T23:59:59')
            if total_min is not None:
                query = query.filter(VentaModel.total >= total_min)
            ventas = query.order_by(VentaModel.id).all()

            resultado = []
            for v in ventas:
                lineas = s.query(TransactionModel).filter_by(venta_id=v.id).all()
                if product_id and not any(l.product_id == product_id for l in lineas):
                    continue
                resultado.append(self._row_to_venta(v, lineas))
            return resultado

    # ── Notificaciones ──────────────────────────────────────

    def save_notification(self, mensaje: str, tipo: str, timestamp: str) -> None:
        with self._Session() as s:
            s.add(NotificationModel(mensaje=mensaje, tipo=tipo, timestamp=timestamp))
            s.commit()

    def get_notifications(self) -> list:
        with self._Session() as s:
            rows = s.query(NotificationModel).order_by(NotificationModel.id.desc()).all()
            return [{'id': n.id, 'mensaje': n.mensaje, 'tipo': n.tipo,
                    'leida': n.leida, 'timestamp': n.timestamp} for n in rows]

    def mark_notification_read(self, notification_id: int) -> None:
        with self._Session() as s:
            n = s.query(NotificationModel).filter_by(id=notification_id).first()
            if n:
                n.leida = True
                s.commit()

    # ── Usuarios ──────────────────────────────────────────

    def get_user(self, username: str):
        """Retorna UserModel o None."""
        with self._Session() as s:
            return s.query(UserModel).filter_by(username=username).first()

    def get_all_users(self) -> list:
        with self._Session() as s:
            return s.query(UserModel).all()

    # ── Clientes ──────────────────────────────────────────

    def get_all_customers(self) -> list:
        with self._Session() as s:
            return s.query(CustomerModel).all()

    def save_customer(self, data: dict) -> None:
        with self._Session() as s:
            s.add(CustomerModel(**data))
            s.commit()

    # ── Conversores ───────────────────────────────────────

    def _row_to_product(self, m: ProductModel) -> Product:
        return Product(product_id=m.product_id, name=m.name, price=m.price,
                       stock=m.stock, category=m.category,
                       description=m.description or '',
                       extra_attrs=json.loads(m.extra_attrs or '{}'))

    def _row_to_venta(self, v: VentaModel, lineas: list) -> dict:
        return {
            'id': v.id,
            'numero_comprobante': v.numero_comprobante,
            'tipo_comprobante': v.tipo_comprobante,
            'cliente_ruc': v.cliente_ruc,
            'cliente_nombre': v.cliente_nombre,
            'metodo_pago': v.metodo_pago,
            'estrategia_descuento': v.estrategia_descuento,
            'subtotal': v.subtotal,
            'igv': v.igv,
            'total': v.total,
            'timestamp': v.timestamp,
            'lineas': [{'product_id': l.product_id, 'product_name': l.product_name,
                       'quantity': l.quantity, 'unit_price': l.unit_price,
                       'line_total': l.line_total} for l in lineas],
        }


assert DatabaseManager() is DatabaseManager(), "Singleton roto"
