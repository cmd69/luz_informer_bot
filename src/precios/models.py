"""DTOs para precios y tramos horarios."""
from dataclasses import dataclass
from datetime import date


@dataclass
class TramoPrecio:
    """Precio en un tramo horario (0-23)."""
    hora: int  # 0-23
    precio: float  # €/kWh


@dataclass
class PreciosDia:
    """Precios de un día completo (24 tramos)."""
    fecha: date
    tramos: list[TramoPrecio]  # 24 elementos, hora 0 a 23

    @property
    def min_precio(self) -> float:
        return min(t.precio for t in self.tramos)

    @property
    def max_precio(self) -> float:
        return max(t.precio for t in self.tramos)

    @property
    def media(self) -> float:
        return sum(t.precio for t in self.tramos) / len(self.tramos) if self.tramos else 0.0

    def precio_hora(self, hora: int) -> float | None:
        for t in self.tramos:
            if t.hora == hora:
                return t.precio
        return None

    def tramos_ordenados(self) -> list[TramoPrecio]:
        return sorted(self.tramos, key=lambda x: x.hora)
