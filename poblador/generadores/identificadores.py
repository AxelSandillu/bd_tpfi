"""Registro de documentos e identificadores.

Mantiene un registro global de documentos usados para que pacientes y
personal nunca compartan número. Genera DNI, matrícula SISA, teléfono,
email y num_asociado respetando las restricciones de la base de datos.
"""

import re
import unicodedata

from config import (
    AREAS_TELEFONICAS,
    EMAIL_DOMINIO,
    SISA_PAIS,
)

LIMITE_EMAIL = 30
LIMITE_TELEFONO = 15
MAX_INT = 2_147_483_647

# Rangos de DNI por año de nacimiento (referencias aproximadas)
# 1960 → 14-18 M, 1990 → 35 M, 2010 → 48-50 M
_DNI_BASE_POR_ANO = [
    (1960, 16_000_000),
    (1990, 35_000_000),
    (2010, 49_000_000),
]


class RegistroIdentificadores:
    """Registro global (singleton) de documentos e identificadores usados."""

    _instancia = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._inicializado = False
        return cls._instancia

    def __init__(self):
        if self._inicializado:
            return
        self.reset()
        self._inicializado = True

    def reset(self):
        """Limpia el registro (útil para tests)."""
        self._dnis_usados = set()
        self._matriculas_usadas = set()
        self._telefonos_usados = set()
        self._emails_usados = set()
        self._num_asociados_usados = set()
        self._contador_num_asociado = 10_000_000

    # ------------------------------------------------------------------
    # DNI correlacionado con año de nacimiento
    # ------------------------------------------------------------------

    @staticmethod
    def dni_por_nacimiento(ano_nacimiento: int, rng) -> int:
        """Genera un DNI correlacionado con el año de nacimiento.

        Referencias aproximadas:
          1960 → 14-18 M
          1990 → 35 M
          2010 → 48-50 M
        """
        if ano_nacimiento <= _DNI_BASE_POR_ANO[0][0]:
            base = _DNI_BASE_POR_ANO[0][1]
        elif ano_nacimiento >= _DNI_BASE_POR_ANO[-1][0]:
            base = _DNI_BASE_POR_ANO[-1][1]
        else:
            for i in range(len(_DNI_BASE_POR_ANO) - 1):
                ano_lo, dni_lo = _DNI_BASE_POR_ANO[i]
                ano_hi, dni_hi = _DNI_BASE_POR_ANO[i + 1]
                if ano_lo < ano_nacimiento <= ano_hi:
                    fraccion = (ano_nacimiento - ano_lo) / (ano_hi - ano_lo)
                    base = int(dni_lo + fraccion * (dni_hi - dni_lo))
                    break
            else:
                base = _DNI_BASE_POR_ANO[-1][1]

        variacion = int(base * 0.10)
        return rng.randint(max(1, base - variacion), base + variacion)

    def generar_dni(self, ano_nacimiento: int, rng, max_intentos: int = 100) -> int:
        """Genera un DNI único correlacionado con el año de nacimiento."""
        for _ in range(max_intentos):
            dni = self.dni_por_nacimiento(ano_nacimiento, rng)
            if dni not in self._dnis_usados:
                self._dnis_usados.add(dni)
                return dni
        raise ValueError(
            f"No se pudo generar un DNI único para año {ano_nacimiento} "
            f"tras {max_intentos} intentos"
        )

    # ------------------------------------------------------------------
    # Matrícula SISA
    # ------------------------------------------------------------------

    MATRICULA_RE = re.compile(r"^[0-9]{2}[1-5][0-9]+$")

    @staticmethod
    def generar_matricula(dni: int, tipo_doc: int = 1) -> str:
        """Genera matrícula SISA: 54 + tipo_doc + documento a 9 dígitos.

        Ejemplo: DNI 30.123.456 → 541030123456
        """
        pais = str(SISA_PAIS).zfill(2)
        tipo = str(tipo_doc)
        doc = str(dni).zfill(9)
        matricula = f"{pais}{tipo}{doc}"
        if not RegistroIdentificadores.validar_matricula(matricula):
            raise ValueError(f"Matrícula inválida: {matricula}")
        return matricula

    @staticmethod
    def validar_matricula(matricula: str) -> bool:
        """Valida la matrícula contra el dominio Matricula."""
        return bool(RegistroIdentificadores.MATRICULA_RE.match(matricula or ""))

    def registrar_matricula(self, matricula: str) -> None:
        """Registra una matrícula como usada."""
        if not self.validar_matricula(matricula):
            raise ValueError(f"Matrícula inválida: {matricula}")
        self._matriculas_usadas.add(matricula)

    def matricula_esta_usada(self, matricula: str) -> bool:
        return matricula in self._matriculas_usadas

    # ------------------------------------------------------------------
    # Teléfono
    # ------------------------------------------------------------------

    TELEFONO_RE = re.compile(r"^\+?[0-9\s\-\(\)]{7,15}$")

    def generar_telefono(self, ciudad: str, rng, max_intentos: int = 100) -> str:
        """Genera teléfono compacto +549 + área + número (máx. 15 chars, UNIQUE)."""
        area = AREAS_TELEFONICAS.get(ciudad)
        if area is None:
            raise ValueError(f"No hay área telefónica para {ciudad}")

        # +549 = 4 chars. Máx. 15 total → dígitos de número = 15 - 4 - len(area)
        digitos_numero = LIMITE_TELEFONO - 4 - len(area)
        if digitos_numero < 1:
            raise ValueError(f"Área {area} demasiado larga para teléfono ≤ 15 chars")
        min_num = 10 ** (digitos_numero - 1)
        max_num = (10**digitos_numero) - 1

        for _ in range(max_intentos):
            numero = f"{rng.randint(min_num, max_num):0{digitos_numero}d}"
            telefono = f"+549{area}{numero}"
            if (
                len(telefono) <= LIMITE_TELEFONO
                and self.TELEFONO_RE.match(telefono)
                and telefono not in self._telefonos_usados
            ):
                self._telefonos_usados.add(telefono)
                return telefono
        raise ValueError(
            f"No se pudo generar un teléfono único para {ciudad} tras "
            f"{max_intentos} intentos"
        )

    # ------------------------------------------------------------------
    # Email
    # ------------------------------------------------------------------

    EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        """Elimina tildes y pasa a minúsculas."""
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
        texto = texto.replace("ñ", "n").replace("Ñ", "N")
        return texto.lower()

    def generar_email(self, nombre: str, apellido: str, rng, max_intentos: int = 100) -> str:
        """Genera email normalizado (sin tildes, máx. 30 chars, UNIQUE)."""
        nombre_norm = self._normalizar_texto(nombre).replace(" ", ".")
        apellido_norm = self._normalizar_texto(apellido).replace(" ", ".")
        base_local = f"{nombre_norm}.{apellido_norm}"
        dominio = EMAIL_DOMINIO
        max_local = LIMITE_EMAIL - len(dominio) - 1  # espacio para @

        for sufijo in [""] + [str(i) for i in range(1, max_intentos + 1)]:
            local = base_local + sufijo
            if len(local) > max_local:
                local = local[:max_local]
            email = f"{local}@{dominio}"
            if (
                len(email) <= LIMITE_EMAIL
                and self.EMAIL_RE.match(email)
                and email not in self._emails_usados
            ):
                self._emails_usados.add(email)
                return email
        raise ValueError(
            f"No se pudo generar un email único para {nombre} {apellido} "
            f"tras {max_intentos} intentos"
        )

    # ------------------------------------------------------------------
    # num_asociado
    # ------------------------------------------------------------------

    def generar_num_asociado(self, rng, max_intentos: int = 1000) -> int:
        """Genera num_asociado UNIQUE dentro del rango de INT."""
        for _ in range(max_intentos):
            num = self._contador_num_asociado
            self._contador_num_asociado += 1
            if num > MAX_INT:
                raise ValueError("Se agotó el rango de INT para num_asociado")
            if num not in self._num_asociados_usados:
                self._num_asociados_usados.add(num)
                return num
        raise ValueError("No se pudo generar un num_asociado único")
