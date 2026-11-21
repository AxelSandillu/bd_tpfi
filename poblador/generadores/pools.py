"""Pools de recursos para la generación de datos en memoria.

Contiene:

- **Pools consumibles** (cada elemento se usa una vez y se quita del pool):
  personal sin servicio, pares (centro, tipo) sin usar, registros todavía no
  internados.
- **Pools reutilizables** (se sortea con reposición): pacientes, horarios,
  obras sociales.

Todo se indexa por atributo (medicos_libres, enfermeros_libres,
servicios_que_internan, etc.) y es reproducible con una semilla.

El método `tomar(n)` sortea y quita `n` elementos; si el pool no alcanza,
lanza `PoolAgotadoError`.
"""

import random
from typing import Any


class PoolAgotadoError(Exception):
    """Se lanza cuando se intenta tomar más elementos de los disponibles en un pool."""


class Pool:
    """Pool genérico de elementos.

    Args:
        nombre: nombre identificador del pool (para mensajes de error).
        elementos: lista inicial de elementos.
        consumible: si True, los elementos tomados se quitan del pool;
            si False, se sortean con reposición.
        rng: generador aleatorio (para reproducibilidad).
    """

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
        # Copia para no mutar la lista original del llamador.
        self._disponibles: list[Any] = list(elementos or [])
        self._usados: list[Any] = []

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def cantidad(self) -> int:
        """Devuelve la cantidad de elementos disponibles."""
        return len(self._disponibles)

    def esta_vacio(self) -> bool:
        """Devuelve True si no hay elementos disponibles."""
        return len(self._disponibles) == 0

    def usados(self) -> list[Any]:
        """Devuelve los elementos ya tomados (solo para consumibles)."""
        return list(self._usados)

    def disponibles(self) -> list[Any]:
        """Devuelve una copia de los elementos disponibles."""
        return list(self._disponibles)

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------

    def agregar(self, elemento: Any) -> None:
        """Agrega un elemento al pool de disponibles."""
        self._disponibles.append(elemento)

    def tomar(self, n: int) -> list[Any]:
        """Sortea y quita `n` elementos del pool.

        Args:
            n: cantidad de elementos a tomar.

        Returns:
            Lista con los `n` elementos sorteados.

        Raises:
            PoolAgotadoError: si el pool no tiene suficientes elementos.
        """
        if n < 0:
            raise ValueError(f"Pool {self.nombre}: no se pueden tomar {n} elementos (negativo).")
        if n > len(self._disponibles):
            raise PoolAgotadoError(
                f"Pool '{self.nombre}' agotado: se pidieron {n} elementos pero "
                f"solo hay {len(self._disponibles)} disponibles."
            )

        # Sortear índices sin reposición para evitar duplicados con dicts.
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
        """Sortea y quita un solo elemento."""
        return self.tomar(1)[0]

    def sortear(self, n: int) -> list[Any]:
        """Sortea `n` elementos con reposición (no los quita del pool).

        Args:
            n: cantidad de elementos a sortear.

        Returns:
            Lista con los `n` elementos sorteados (pueden repetirse).

        Raises:
            PoolAgotadoError: si el pool está vacío.
        """
        if self.esta_vacio():
            raise PoolAgotadoError(
                f"Pool '{self.nombre}' está vacío: no se puede sortear."
            )
        return [self._rng.choice(self._disponibles) for _ in range(n)]

    def sortear_uno(self) -> Any:
        """Sortea un solo elemento con reposición."""
        return self.sortear(1)[0]


class Pools:
    """Contenedor de pools indexados por nombre.

    Permite registrar pools arbitrarios y acceder a ellos por nombre.
    Incluye métodos de conveniencia para los pools típicos del generador
    clínico (medicos_libres, enfermeros_libres, pacientes, etc.).
    """

    def __init__(self, rng: random.Random | None = None, seed: int | None = None):
        if rng is None:
            rng = random.Random(seed if seed is not None else 42)
        self._rng = rng
        self._pools: dict[str, Pool] = {}

    # ------------------------------------------------------------------
    # Registro y acceso genérico
    # ------------------------------------------------------------------

    def registrar(self, nombre: str, elementos: list[Any], consumible: bool = True) -> Pool:
        """Registra un nuevo pool y devuelve su instancia."""
        pool = Pool(nombre, elementos, consumible=consumible, rng=self._rng)
        self._pools[nombre] = pool
        return pool

    def obtener(self, nombre: str) -> Pool:
        """Devuelve el pool registrado con `nombre`."""
        if nombre not in self._pools:
            raise KeyError(f"No existe el pool '{nombre}'.")
        return self._pools[nombre]

    def __contains__(self, nombre: str) -> bool:
        return nombre in self._pools

    def nombres(self) -> list[str]:
        """Devuelve los nombres de todos los pools registrados."""
        return list(self._pools.keys())

    # ------------------------------------------------------------------
    # Métodos de conveniencia para pools típicos del generador
    # ------------------------------------------------------------------

    def personal_sin_servicio(self, personal: list[dict]) -> Pool:
        """Pool consumible de personal sin asignar a ningún servicio."""
        return self.registrar("personal_sin_servicio", list(personal), consumible=True)

    def medicos_libres(self, medicos: list[dict]) -> Pool:
        """Pool consumible de médicos disponibles."""
        return self.registrar("medicos_libres", list(medicos), consumible=True)

    def enfermeros_libres(self, enfermeros: list[dict]) -> Pool:
        """Pool consumible de enfermeros disponibles."""
        return self.registrar("enfermeros_libres", list(enfermeros), consumible=True)

    def pares_centro_tipo(self, pares: list[dict]) -> Pool:
        """Pool consumible de pares (centro, tipo) sin usar."""
        return self.registrar("pares_centro_tipo", list(pares), consumible=True)

    def registros_no_internados(self, registros: list[dict]) -> Pool:
        """Pool consumible de registros de HC todavía no internados."""
        return self.registrar("registros_no_internados", list(registros), consumible=True)

    def pacientes(self, pacientes: list[dict]) -> Pool:
        """Pool reutilizable de pacientes (sorteo con reposición)."""
        return self.registrar("pacientes", list(pacientes), consumible=False)

    def horarios(self, horarios: list[dict]) -> Pool:
        """Pool reutilizable de horarios (sorteo con reposición)."""
        return self.registrar("horarios", list(horarios), consumible=False)

    def obras_sociales(self, obras: list[dict]) -> Pool:
        """Pool reutilizable de obras sociales (sorteo con reposición)."""
        return self.registrar("obras_sociales", list(obras), consumible=False)

    def servicios_que_internan(self, servicios: list[dict]) -> Pool:
        """Pool reutilizable de servicios que admiten internación."""
        return self.registrar("servicios_que_internan", list(servicios), consumible=False)
