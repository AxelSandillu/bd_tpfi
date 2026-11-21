"""Pools de recursos para la generación de datos en memoria.

Contiene los consumibles (cada elemento se usa una vez) y los reutilizables
(se sortea con reposición), indexados por atributo.

El método `tomar(n)` sortea y quita; si no alcanza, lanza `PoolAgotadoError`.
"""

import random
from typing import Any


class PoolAgotadoError(Exception):
    """Se lanza cuando se intenta tomar más elementos de los disponibles en un pool."""


class Pool:
    """Pool genérico de elementos."""

    def __init__(
        self,
        nombre: str,
        elementos: list[Any] | None = None,
        consumible: bool = True,
        rng: random.Random | None = None,
    ):
        self.nombre = nombre
        self.consumible = consumible
        self._rng = rng or random.Random()
        self._disponibles: list[Any] = list(elementos or [])
        self._usados: list[Any] = []

    def cantidad(self) -> int:
        return len(self._disponibles)

    def esta_vacio(self) -> bool:
        return len(self._disponibles) == 0

    def usados(self) -> list[Any]:
        return list(self._usados)

    def disponibles(self) -> list[Any]:
        return list(self._disponibles)

    def agregar(self, elemento: Any) -> None:
        self._disponibles.append(elemento)

    def tomar(self, n: int) -> list[Any]:
        if n < 0:
            raise ValueError(
                f"Pool {self.nombre}: no se pueden tomar {n} elementos (negativo)."
            )
        if n > len(self._disponibles):
            raise PoolAgotadoError(
                f"Pool '{self.nombre}' agotado: se pidieron {n} elementos pero "
                f"solo hay {len(self._disponibles)} disponibles."
            )

        indices = self._rng.sample(range(len(self._disponibles)), n)
        indices.sort(reverse=True)

        seleccionados: list[Any] = []
        for i in indices:
            elemento = self._disponibles.pop(i)
            seleccionados.append(elemento)
            if self.consumible:
                self._usados.append(elemento)

        return seleccionados

    def tomar_uno(self) -> Any:
        return self.tomar(1)[0]

    def sortear(self, n: int) -> list[Any]:
        if self.esta_vacio():
            raise PoolAgotadoError(
                f"Pool '{self.nombre}' está vacío: no se puede sortear."
            )
        return [self._rng.choice(self._disponibles) for _ in range(n)]

    def sortear_uno(self) -> Any:
        return self.sortear(1)[0]


class Pools:
    """Contenedor de pools indexados por nombre."""

    def __init__(self, rng: random.Random | None = None, seed: int | None = None):
        if rng is None:
            rng = random.Random(seed if seed is not None else 42)
        self._rng = rng
        self._pools: dict[str, Pool] = {}

    def registrar(self, nombre: str, elementos: list[Any], consumible: bool = True) -> Pool:
        pool = Pool(nombre, elementos, consumible=consumible, rng=self._rng)
        self._pools[nombre] = pool
        return pool

    def obtener(self, nombre: str) -> Pool:
        if nombre not in self._pools:
            raise KeyError(f"No existe el pool '{nombre}'.")
        return self._pools[nombre]

    def __contains__(self, nombre: str) -> bool:
        return nombre in self._pools

    def nombres(self) -> list[str]:
        return list(self._pools.keys())

    def personal_sin_servicio(self, personal: list[dict]) -> Pool:
        return self.registrar("personal_sin_servicio", list(personal), consumible=True)

    def medicos_libres(self, medicos: list[dict]) -> Pool:
        return self.registrar("medicos_libres", list(medicos), consumible=True)

    def enfermeros_libres(self, enfermeros: list[dict]) -> Pool:
        return self.registrar("enfermeros_libres", list(enfermeros), consumible=True)

    def pares_centro_tipo(self, pares: list[dict]) -> Pool:
        return self.registrar("pares_centro_tipo", list(pares), consumible=True)

    def registros_no_internados(self, registros: list[dict]) -> Pool:
        return self.registrar("registros_no_internados", list(registros), consumible=True)

    def pacientes(self, pacientes: list[dict]) -> Pool:
        return self.registrar("pacientes", list(pacientes), consumible=False)

    def horarios(self, horarios: list[dict]) -> Pool:
        return self.registrar("horarios", list(horarios), consumible=False)

    def obras_sociales(self, obras: list[dict]) -> Pool:
        return self.registrar("obras_sociales", list(obras), consumible=False)

    def servicios_que_internan(self, servicios: list[dict]) -> Pool:
        return self.registrar("servicios_que_internan", list(servicios), consumible=False)
