-- -----------------------------------------------
-- trg_centro_de_salud_inauguración
-- Descripción: verifica que la fecha de inauguración sea anterior a hoy.

-- Caso Base: fecha de inauguración anterior a hoy (28/10/2026).
-- Resultado esperado: el centro de salud se inserta correctamente.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES (9001, 1, 'Centro Test Inauguración A', '2026-10-28', 'Calle Test', 100);

ROLLBACK;


-- OBSERVACIÓN: la función usa NEW.inaguracion >= CURRENT_DATE, por lo que la
-- implementación real lanza excepción. Se deja el caso para evidenciar la
-- discrepancia entre el plan de testing y el código.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES (9002, 1, 'Centro Test Inauguración B', CURRENT_DATE, 'Calle Test', 100);

ROLLBACK;


-- Resultado esperado: excepción indicando que la fecha debe ser anterior a hoy.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES (9003, 1, 'Centro Test Inauguración C', '2048-01-10', 'Calle Test', 100);

ROLLBACK;


-- -----------------------------------------------
-- trg_paciente_nacimiento
-- Descripción: verifica que la fecha de nacimiento sea anterior a hoy.

-- Caso Base: paciente con nacimiento el 28/10/1996.
-- Resultado esperado: el paciente es registrado correctamente.
BEGIN;

INSERT INTO paciente (dni, nombre, apellido, nacimiento)
VALUES (90000001, 'Test', 'Paciente Base', '1996-10-28');

ROLLBACK;


-- Caso Excepción: paciente con nacimiento el 28/10/2048.
-- Resultado esperado: excepción por fecha de nacimiento inválida.
BEGIN;

INSERT INTO paciente (dni, nombre, apellido, nacimiento)
VALUES (90000002, 'Test', 'Paciente Futuro', '2048-10-28');

ROLLBACK;


-- -----------------------------------------------
-- trg_personal_validar_datos
-- Descripción: verifica que el teléfono, email y edad sean válidos.

-- Caso Base: personal con todos los datos válidos.
-- Resultado esperado: el personal se ingresa correctamente.
BEGIN;

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES ('991000001', 'Test', 'Datos Validos', '+549110000001', 'test.valido@example.com', '1996-10-28', 'Médico');

ROLLBACK;


-- Caso Excepción: personal con email inválido.
-- Resultado esperado: excepción informando que el email es inválido.
BEGIN;

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES ('991000002', 'Test', 'Email Invalido', '+549110000002', 'correo-invalido', '1996-10-28', 'Médico');

ROLLBACK;


-- Caso Excepción: personal con teléfono inválido.
-- Resultado esperado: excepción informando que el teléfono es inválido.
BEGIN;

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES ('991000003', 'Test', 'Telefono Invalido', '12-34', 'test.telefono@example.com', '1996-10-28', 'Médico');

ROLLBACK;


-- Caso Excepción: personal menor de edad.
-- Resultado esperado: excepción informando que el personal debe ser mayor de edad.
BEGIN;

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES ('991000004', 'Test', 'Menor Edad', '+549110000004', 'test.menor@example.com', CURRENT_DATE - INTERVAL '10 years', 'Médico');

ROLLBACK;


-- -----------------------------------------------
-- trg_personal_nacimiento
-- Descripción: verifica que la fecha de nacimiento sea anterior a hoy.

-- Caso Base: personal con nacimiento el 28/10/1996.
-- Resultado esperado: el personal es registrado correctamente.
BEGIN;

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES ('991000005', 'Test', 'Nacimiento Base', '+549110000005', 'test.nacimiento@example.com', '1996-10-28', 'Médico');

ROLLBACK;


-- Caso Excepción: personal con nacimiento el 28/10/2048.
-- Resultado esperado: excepción por fecha de nacimiento inválida.
BEGIN;

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES ('991000006', 'Test', 'Nacimiento Futuro', '+549110000006', 'test.nac.fut@example.com', '2048-10-28', 'Médico');

ROLLBACK;


-- -----------------------------------------------
-- trg_servicio_personal_encargado
-- Descripción: verifica que el personal a cargo sea un médico.

-- Caso Base: se asigna como encargado de un servicio a un médico.
-- Resultado esperado: no produce error, el médico queda como encargado.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES (9001, 1, 'Centro Test Encargado A', '2000-01-01', 'Calle Test', 100);

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES ('991000007', 'Test', 'Medico Encargado', '+549110000007', 'test.med.enc@example.com', '1980-01-01', 'Médico');

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio, matricula_encargado)
OVERRIDING SYSTEM VALUE
VALUES (9001, 9001, 'Medicina General', '991000007');

ROLLBACK;


-- Caso Excepción: se asigna como encargado de un servicio a un enfermero.
-- Resultado esperado: excepción indicando que el encargado del servicio debe ser un médico.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES (9001, 1, 'Centro Test Encargado B', '2000-01-01', 'Calle Test', 100);

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES ('991000008', 'Test', 'Enfermero Encargado', '+549110000008', 'test.enf.enc@example.com', '1980-01-01', 'Enfermero');

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio, matricula_encargado)
OVERRIDING SYSTEM VALUE
VALUES (9001, 9001, 'Medicina General', '991000008');

ROLLBACK;


-- -----------------------------------------------
-- trg_servicio_centro_unico
-- Descripción: verifica que en cada centro de salud no haya más de un servicio de un mismo tipo.

-- Caso Base: se incorpora un nuevo servicio a un centro de salud, de un tipo que no tenía previamente.
-- Resultado esperado: el servicio es creado correctamente.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES (9001, 1, 'Centro Test Servicio A', '2000-01-01', 'Calle Test', 100);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio, matricula_encargado)
OVERRIDING SYSTEM VALUE
VALUES (9001, 9001, 'Medicina General', NULL);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio, matricula_encargado)
OVERRIDING SYSTEM VALUE
VALUES (9002, 9001, 'Cardiología', NULL);

ROLLBACK;


-- Caso Excepción: se incorpora un nuevo servicio a un centro de salud, de un tipo que ya tenía previamente.
-- Resultado esperado: excepción indicando que el centro de salud ya tenía un servicio de ese tipo.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES (9001, 1, 'Centro Test Servicio B', '2000-01-01', 'Calle Test', 100);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio, matricula_encargado)
OVERRIDING SYSTEM VALUE
VALUES (9001, 9001, 'Medicina General', NULL);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio, matricula_encargado)
OVERRIDING SYSTEM VALUE
VALUES (9002, 9001, 'Medicina General', NULL);

ROLLBACK;


-- -----------------------------------------------
-- trg_registro_hc_encargado
-- Descripción: verifica que el médico que atendió trabaje en el servicio utilizado y sea un médico.

-- Caso Base: se crea un registro donde un médico válido lo atendió.
-- Resultado esperado: el trigger deja pasar la inserción sin emitir excepción.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES
    (9001, 1, 'Centro Test HC A', '2000-01-01', 'Calle Test', 100),
    (9002, 1, 'Centro Test HC B', '2000-01-01', 'Calle Test', 200);

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos)
VALUES ('Tipo Test Axel', 5, 5);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio, matricula_encargado)
OVERRIDING SYSTEM VALUE
VALUES
    (9001, 9001, 'Tipo Test Axel', NULL),
    (9002, 9002, 'Tipo Test Axel', NULL);

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES
    ('991000010', 'Test', 'Medico Uno', '+549110000010', 'test.med.uno@example.com', '1980-01-01', 'Médico'),
    ('991000011', 'Test', 'Medico Dos', '+549110000011', 'test.med.dos@example.com', '1980-01-01', 'Médico'),
    ('991000012', 'Test', 'Enfermero Uno', '+549110000012', 'test.enf.uno@example.com', '1980-01-01', 'Enfermero');

INSERT INTO paciente (dni, nombre, apellido, nacimiento)
VALUES (90000010, 'Test', 'Paciente HC', '1990-01-01');

INSERT INTO personal_servicio (id_servicio, matricula_personal)
VALUES
    (9001, '991000010'),
    (9001, '991000012'),
    (9002, '991000011');

INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
VALUES (9001, 90000010, '991000010', '2026-01-01', 'Test', 'Test');

ROLLBACK;


-- Caso Excepción: se crea un registro donde fue atendido por un enfermero.
-- Resultado esperado: excepción indicando que un enfermero no puede atender a pacientes.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES
    (9001, 1, 'Centro Test HC C', '2000-01-01', 'Calle Test', 100),
    (9002, 1, 'Centro Test HC D', '2000-01-01', 'Calle Test', 200);

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos)
VALUES ('Tipo Test Axel', 5, 5);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio, matricula_encargado)
OVERRIDING SYSTEM VALUE
VALUES
    (9001, 9001, 'Tipo Test Axel', NULL),
    (9002, 9002, 'Tipo Test Axel', NULL);

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES
    ('991000010', 'Test', 'Medico Uno', '+549110000010', 'test.med.uno@example.com', '1980-01-01', 'Médico'),
    ('991000011', 'Test', 'Medico Dos', '+549110000011', 'test.med.dos@example.com', '1980-01-01', 'Médico'),
    ('991000012', 'Test', 'Enfermero Uno', '+549110000012', 'test.enf.uno@example.com', '1980-01-01', 'Enfermero');

INSERT INTO paciente (dni, nombre, apellido, nacimiento)
VALUES (90000011, 'Test', 'Paciente HC Enfermero', '1990-01-01');

INSERT INTO personal_servicio (id_servicio, matricula_personal)
VALUES
    (9001, '991000010'),
    (9001, '991000012'),
    (9002, '991000011');

INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
VALUES (9001, 90000011, '991000012', '2026-01-01', 'Test', 'Test');

ROLLBACK;


-- Caso Excepción: se crea un registro donde fue atendido por un médico de otro servicio.
-- Resultado esperado: excepción indicando que un médico no puede atender en un servicio en el que no trabaja.
BEGIN;

INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura)
OVERRIDING SYSTEM VALUE
VALUES
    (9001, 1, 'Centro Test HC E', '2000-01-01', 'Calle Test', 100),
    (9002, 1, 'Centro Test HC F', '2000-01-01', 'Calle Test', 200);

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos)
VALUES ('Tipo Test Axel', 5, 5);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio, matricula_encargado)
OVERRIDING SYSTEM VALUE
VALUES
    (9001, 9001, 'Tipo Test Axel', NULL),
    (9002, 9002, 'Tipo Test Axel', NULL);

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol)
VALUES
    ('991000010', 'Test', 'Medico Uno', '+549110000010', 'test.med.uno@example.com', '1980-01-01', 'Médico'),
    ('991000011', 'Test', 'Medico Dos', '+549110000011', 'test.med.dos@example.com', '1980-01-01', 'Médico'),
    ('991000012', 'Test', 'Enfermero Uno', '+549110000012', 'test.enf.uno@example.com', '1980-01-01', 'Enfermero');

INSERT INTO paciente (dni, nombre, apellido, nacimiento)
VALUES (90000012, 'Test', 'Paciente HC Otro Servicio', '1990-01-01');

INSERT INTO personal_servicio (id_servicio, matricula_personal)
VALUES
    (9001, '991000010'),
    (9001, '991000012'),
    (9002, '991000011');

INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
VALUES (9001, 90000012, '991000011', '2026-01-01', 'Test', 'Test');

ROLLBACK;
