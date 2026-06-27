"""Capa de datos: Singleton DatabaseManager con SQLAlchemy + SQLite."""
import json
import os
from dataclasses import dataclass, field

from sqlalchemy import Column, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash


# ── Modelos SQLAlchemy ────────────────────────────────────

class Base(DeclarativeBase):
    pass


class ProductModel(Base):
    __tablename__ = 'products'
    product_id  = Column(String, primary_key=True)
    name        = Column(String, nullable=False)
    price       = Column(Float,  nullable=False)
    stock       = Column(Integer, nullable=False)
    category    = Column(String, nullable=False)
    extra_attrs = Column(Text, default='{}')


class TransactionModel(Base):
    __tablename__ = 'transactions'
    id           = Column(Integer, primary_key=True, autoincrement=True)
    product_id   = Column(String, nullable=False)
    product_name = Column(String, nullable=False)
    quantity     = Column(Integer, nullable=False)
    unit_price   = Column(Float, nullable=False)
    total        = Column(Float, nullable=False)
    strategy     = Column(String, nullable=False)
    timestamp    = Column(String, nullable=False)


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

    def get_all_products(self) -> list:
        with self._Session() as s:
            return [self._row_to_product(m) for m in s.query(ProductModel).all()]

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
                m.extra_attrs = json.dumps(product.extra_attrs)
            else:
                s.add(ProductModel(product_id=product.product_id, name=product.name,
                                   price=product.price, stock=product.stock,
                                   category=product.category,
                                   extra_attrs=json.dumps(product.extra_attrs)))
            s.commit()

    # ── Transacciones ─────────────────────────────────────

    def save_transaction(self, transaction: dict) -> None:
        with self._Session() as s:
            s.add(TransactionModel(**{k: transaction[k] for k in
                  ['product_id','product_name','quantity','unit_price','total','strategy','timestamp']}))
            s.commit()

    def get_transactions(self) -> list:
        with self._Session() as s:
            rows = s.query(TransactionModel).order_by(TransactionModel.id).all()
            return [self._row_to_dict(m) for m in rows]

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
                       extra_attrs=json.loads(m.extra_attrs or '{}'))

    def _row_to_dict(self, m: TransactionModel) -> dict:
        return {'product_id': m.product_id, 'product_name': m.product_name,
                'quantity': m.quantity, 'unit_price': m.unit_price,
                'total': m.total, 'strategy': m.strategy, 'timestamp': m.timestamp}


assert DatabaseManager() is DatabaseManager(), "Singleton roto"
