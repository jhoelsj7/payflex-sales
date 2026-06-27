"""Capa de datos: fábricas de productos (patrón Factory Method)."""
from abc import ABC, abstractmethod
from datetime import date

from data.database import DatabaseManager, Product


class ProductFactory(ABC):
    """Fábrica abstracta de productos.

    Define el contrato para crear y registrar productos tipados.
    Subclases concretas implementan `create_product` con atributos propios.
    """

    @abstractmethod
    def create_product(self, product_id: str, name: str, price: float,
                       stock: int, **kwargs) -> Product:
        """Crea y retorna una instancia de Product con atributos específicos."""

    def register_product(self, product_id: str, name: str, price: float,
                         stock: int, **kwargs) -> Product:
        """Crea el producto y lo persiste en DatabaseManager."""
        product = self.create_product(product_id, name, price, stock, **kwargs)
        DatabaseManager().save_product(product)
        return product


class ElectronicProductFactory(ProductFactory):
    """Fábrica de productos electrónicos con atributo warranty_months."""

    def create_product(self, product_id: str, name: str, price: float,
                       stock: int, **kwargs) -> Product:
        """Crea un producto electrónico con meses de garantía."""
        return Product(
            product_id=product_id,
            name=name,
            price=price,
            stock=stock,
            category='electronic',
            extra_attrs={'warranty_months': kwargs.get('warranty_months', 12)},
        )


class ClothingProductFactory(ProductFactory):
    """Fábrica de prendas de vestir con atributos size y material."""

    def create_product(self, product_id: str, name: str, price: float,
                       stock: int, **kwargs) -> Product:
        """Crea un producto de ropa con talla y material."""
        return Product(
            product_id=product_id,
            name=name,
            price=price,
            stock=stock,
            category='clothing',
            extra_attrs={
                'size': kwargs.get('size', 'M'),
                'material': kwargs.get('material', 'algodón'),
            },
        )


class FoodProductFactory(ProductFactory):
    """Fábrica de productos alimenticios con atributo expiry_date."""

    def create_product(self, product_id: str, name: str, price: float,
                       stock: int, **kwargs) -> Product:
        """Crea un producto alimenticio con fecha de vencimiento."""
        return Product(
            product_id=product_id,
            name=name,
            price=price,
            stock=stock,
            category='food',
            extra_attrs={'expiry_date': kwargs.get('expiry_date', str(date.today()))},
        )
