"""Tests para el registro de documentos e identificadores (issue #8)."""

import random

from generadores.identificadores import RegistroIdentificadores


def setup_function():
    """Limpia el registro antes de cada test."""
    RegistroIdentificadores().reset()


def test_dni_correlacionado_con_nacimiento():
    """El DNI debe crecer con el año de nacimiento."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    dni_1960 = reg.dni_por_nacimiento(1960, rng)
    dni_1990 = reg.dni_por_nacimiento(1990, rng)
    dni_2010 = reg.dni_por_nacimiento(2010, rng)

    assert 13_000_000 <= dni_1960 <= 19_000_000, f"DNI 1960 fuera de rango: {dni_1960}"
    assert 30_000_000 <= dni_1990 <= 40_000_000, f"DNI 1990 fuera de rango: {dni_1990}"
    assert 43_000_000 <= dni_2010 <= 54_000_000, f"DNI 2010 fuera de rango: {dni_2010}"
    assert dni_1960 < dni_1990 < dni_2010


def test_dni_unico():
    """Dos personas no pueden compartir el mismo DNI."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    dnis = set()
    for _ in range(50):
        dni = reg.generar_dni(1990, rng)
        assert dni not in dnis, f"DNI duplicado: {dni}"
        dnis.add(dni)

    assert len(dnis) == 50


def test_matricula_formato_y_regex():
    """La matrícula SISA debe tener el formato correcto y pasar el regex del dominio."""
    reg = RegistroIdentificadores()

    # DNI 30.123.456 → 541030123456
    matricula = reg.generar_matricula(30123456, tipo_doc=1)
    assert matricula == "541030123456", f"Esperado 541030123456, se obtuvo {matricula}"
    assert reg.validar_matricula(matricula)

    # Otro ejemplo
    matricula2 = reg.generar_matricula(12345, tipo_doc=1)
    assert matricula2 == "541000012345"
    assert reg.validar_matricula(matricula2)

    # Tipo de documento 5 (pasaporte)
    matricula3 = reg.generar_matricula(999999999, tipo_doc=5)
    assert matricula3 == "545999999999"
    assert reg.validar_matricula(matricula3)


def test_matricula_regex_rechaza_valores_invalidos():
    """El regex del dominio Matricula rechaza valores fuera de formato."""
    reg = RegistroIdentificadores()
    # Tipo de documento 0 o 6 no están en 1-5
    assert not reg.validar_matricula("540123456789")  # tipo doc = 0
    assert not reg.validar_matricula("546123456789")  # tipo doc = 6
    assert not reg.validar_matricula("abc123456789")  # no numérico
    assert not reg.validar_matricula("")  # vacío


def test_matricula_unica():
    """Dos personas no pueden compartir la misma matrícula."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    matriculas = set()
    for i in range(50):
        dni = reg.generar_dni(1990, rng)
        matricula = reg.generar_matricula(dni, tipo_doc=1)
        reg.registrar_matricula(matricula)
        assert matricula not in matriculas, f"Matrícula duplicada: {matricula}"
        assert reg.validar_matricula(matricula)
        matriculas.add(matricula)

    assert len(matriculas) == 50


def test_telefono_formato_y_longitud():
    """El teléfono debe ser +549 + área + número, máx. 15 chars, pasar regex."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    tel = reg.generar_telefono("Paraná", rng)
    assert tel.startswith("+549343")
    assert len(tel) <= 15
    assert reg.TELEFONO_RE.match(tel)
    assert sum(c.isdigit() for c in tel) >= 7

    tel_con = reg.generar_telefono("Concordia", rng)
    assert tel_con.startswith("+549345")

    tel_gua = reg.generar_telefono("Gualeguaychú", rng)
    assert tel_gua.startswith("+5493446")

    tel_cdu = reg.generar_telefono("Concepción del Uruguay", rng)
    assert tel_cdu.startswith("+5493442")


def test_telefono_unico():
    """Dos personas no pueden compartir el mismo teléfono."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    telefonos = set()
    for _ in range(30):
        tel = reg.generar_telefono("Paraná", rng)
        assert tel not in telefonos, f"Teléfono duplicado: {tel}"
        telefonos.add(tel)

    assert len(telefonos) == 30


def test_email_normalizado_y_longitud():
    """El email debe estar normalizado (sin tildes), máx. 30 chars y pasar regex."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    email = reg.generar_email("José María", "González", rng)
    assert "@" in email
    assert email.endswith("@example.com")
    assert len(email) <= 30
    assert reg.EMAIL_RE.match(email)
    # Sin tildes ni ñ
    assert "á" not in email and "é" not in email and "í" not in email
    assert "ó" not in email and "ú" not in email and "ñ" not in email
    assert "Á" not in email and "É" not in email


def test_email_unico():
    """Dos personas no pueden compartir el mismo email."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    emails = set()
    for i in range(30):
        email = reg.generar_email(f"Nombre{i}", "Apellido", rng)
        assert email not in emails, f"Email duplicado: {email}"
        assert len(email) <= 30
        emails.add(email)

    assert len(emails) == 30


def test_email_sufijo_numerico_si_colision():
    """Si hay colisión, se agrega un sufijo numérico."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    e1 = reg.generar_email("Ana", "Pérez", rng)
    e2 = reg.generar_email("Ana", "Pérez", rng)
    assert e1 != e2
    assert e2.endswith("1@example.com") or e2.endswith("2@example.com")


def test_num_asociado_unique_y_dentro_int():
    """num_asociado debe ser único y estar dentro del rango de INT."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    nums = set()
    for _ in range(50):
        num = reg.generar_num_asociado(rng)
        assert 0 <= num <= 2_147_483_647, f"num_asociado fuera de rango INT: {num}"
        assert num not in nums, f"num_asociado duplicado: {num}"
        nums.add(num)

    assert len(nums) == 50


def test_pacientes_y_personal_no_comparten_dni():
    """El registro global impide que pacientes y personal compartan DNI."""
    reg = RegistroIdentificadores()
    rng = random.Random(42)

    dni_paciente = reg.generar_dni(1985, rng)
    # El mismo DNI no debería generarse para personal
    with_reg = RegistroIdentificadores()  # mismo singleton
    for _ in range(200):
        dni = reg.generar_dni(1985, rng)
        assert dni != dni_paciente, f"Paciente y personal comparten DNI: {dni_paciente}"
