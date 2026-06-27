"""Capa de negocio: estrategias de descuento (patrón Strategy)."""
from abc import ABC, abstractmethod


class DiscountStrategy(ABC):
    """Interfaz base para algoritmos de descuento intercambiables."""

    @abstractmethod
    def calculate_discount(self, original_price: float, quantity: int) -> float:
        """Calcula y retorna el total aplicando el descuento correspondiente."""

    @abstractmethod
    def get_description(self) -> str:
        """Retorna descripción legible de la estrategia activa."""


class NoDiscountStrategy(DiscountStrategy):
    """Estrategia sin descuento: precio * cantidad."""

    def calculate_discount(self, original_price: float, quantity: int) -> float:
        """Retorna el subtotal sin ningún descuento."""
        return original_price * quantity

    def get_description(self) -> str:
        """Retorna 'Sin descuento'."""
        return "Sin descuento"


class PercentageDiscountStrategy(DiscountStrategy):
    """Estrategia de descuento por porcentaje configurable."""

    def __init__(self, pct: float):
        """Inicializa con el porcentaje de descuento.

        Raises:
            ValueError: si pct no está en [0, 100].
        """
        if not (0 <= pct <= 100):
            raise ValueError(
                f"El porcentaje debe estar entre 0 y 100, recibido: {pct}"
            )
        self._pct = pct

    def calculate_discount(self, original_price: float, quantity: int) -> float:
        """Aplica descuento porcentual: subtotal * (1 - pct/100)."""
        subtotal = original_price * quantity
        return subtotal * (1 - self._pct / 100)

    def get_description(self) -> str:
        """Retorna descripción con el porcentaje configurado."""
        return f"Descuento {self._pct:.0f}%"


class VIPClientStrategy(DiscountStrategy):
    """Estrategia VIP: 20% base + 5% extra si quantity >= 5."""

    def calculate_discount(self, original_price: float, quantity: int) -> float:
        """Aplica 20% base; 25% total si la cantidad es 5 o más."""
        subtotal = original_price * quantity
        if quantity >= 5:
            return subtotal * 0.75
        return subtotal * 0.80

    def get_description(self) -> str:
        """Retorna descripción de la estrategia VIP."""
        return "Cliente VIP (20% base + 5% extra si cantidad >= 5)"


class SeasonalDiscountStrategy(DiscountStrategy):
    """Estrategia de temporada con porcentaje configurable (15% por defecto)."""

    def __init__(self, pct: float = 0.15):
        """Inicializa con el porcentaje de descuento de temporada."""
        self._pct = pct

    def calculate_discount(self, original_price: float, quantity: int) -> float:
        """Aplica descuento de temporada: subtotal * (1 - pct)."""
        subtotal = original_price * quantity
        return subtotal * (1 - self._pct)

    def get_description(self) -> str:
        """Retorna descripción con el porcentaje de temporada."""
        return f"Temporada ({int(self._pct * 100)}%)"
