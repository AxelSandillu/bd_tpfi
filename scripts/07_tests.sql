-- EJECUTAR TEST POR TEST
-- -----------------------------------------------

-- Tests triggers

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

-- -----------------------------------------------
-- trg_internacion_ingreso

-- Excepción: fecha ingreso distinta a registro HC
-- registro_hc id=1 tiene dia_visita='2026-11-17'
-- Resultado esperado: se lanza una excepción indicando que el inicio de la internación debe ser el mismo día que el que figura en el registro HC.
BEGIN;

INSERT INTO internacion (id_registro_hc, fecha_ingreso, fecha_egreso) VALUES (1, '2026-11-18', NULL);

ROLLBACK;

-- -----------------------------------------------
-- trg_internacion_egreso

-- Base: actualizar internación sin egreso con fecha posterior
-- internacion id=107 tiene fecha_ingreso='2026-11-05', fecha_egreso=NULL
-- Resultado esperado: la internación se actualiza sin problemas.
BEGIN;

UPDATE internacion SET fecha_egreso = '2026-11-10' WHERE id = 107;

ROLLBACK;

-- Excepción: actualizar internación sin egreso con fecha anterior
-- internacion id=108 tiene fecha_ingreso='2026-11-05', fecha_egreso=NULL
-- Resultado esperado: se lanza una excepción indicando que la fecha de egreso no puede ser anterior a la de ingreso.
BEGIN;

UPDATE internacion SET fecha_egreso = '2026-11-04' WHERE id = 108;

ROLLBACK;

-- -----------------------------------------------
-- trg_personal_servicio_max_personal

-- Base: agregar enfermero a servicio con cupo
-- servicio 60 (Pediatría general, max 2 enfermeros, actual 0 enfermeros)
-- enfermero 541026060241 (Elisa Caballero) tiene Pediatría, NO está en personal_servicio
-- Resultado esperado: el nuevo personal es asignado correctamente.
BEGIN;

INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (60, '541026060241');

ROLLBACK;

-- Excepción: agregar médico a servicio sin cupo
-- servicio 8 (Medicina General, max 1 médico, actual 1 médico: 541016446866)
-- médico 541018990279 (Yunnuel Arevalo) tiene Medicina General, NO está en personal_servicio
-- Resultado esperado: se indica que ya no hay cupo para nuevo personal del tipo (médico o enfermero) ingresado.
BEGIN;

INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (8, '541018990279');

ROLLBACK;

-- -----------------------------------------------
-- trg_personal_servicio_especialidad

-- Base: agregar enfermero CON especialidades requeridas
-- servicio 30 (Neurología, max 2 enfermeros, actual 0 enfermeros) requiere Neurología
-- enfermero 541038950382 (Luis Bravo) tiene Neurología, NO está en personal_servicio
-- Resultado esperado: el nuevo personal se agrega correctamente al servicio.
BEGIN;

INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (30, '541038950382');

ROLLBACK;

-- Excepción: agregar enfermero SIN especialidades requeridas
-- servicio 30 (Neurología) requiere Neurología
-- enfermero 541026060241 (Elisa Caballero) tiene Pediatría, NO tiene Neurología, NO está en personal_servicio
-- Resultado esperado: se lanza una excepción diciendo que el personal no cumple con las especialidades requeridas y cuales son.
BEGIN;

INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (30, '541026060241');

ROLLBACK;

-- -----------------------------------------------
-- trg_personal_servicio_superposición

-- Base: agregar enfermero a servicio SIN superposición
-- enfermero 541021704836 (Nelly Leyva) está en servicio 10 (Pediatría general)
-- servicio 10 horarios: Miércoles 08-12, Domingo 10-18, Sábado 15-21
-- servicio 66 (Pediatría general) horarios: Martes 18-23, Domingo 18-23 (límite 18 no superpone con 10-18)
-- Resultado esperado: el empleado es asignado correctamente.
BEGIN;

INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (66, '541021704836');

ROLLBACK;

-- Excepción: agregar enfermero a servicio CON superposición
-- mismo enfermero 541021704836 en servicio 10
-- servicio 68 (Pediatría general) horarios: Martes 10-18, Sábado 14-20
-- Superposición con servicio 10 en Sábado (15-21 vs 14-20)
-- Resultado esperado: se activa una excepción indicando que ya trabaja en otro servicio cuyos horarios se superponen con el servicio donde se lo quiere incluir.
BEGIN;

INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (68, '541021704836');

ROLLBACK;

-- Tests vistas

-- -----------------------------------------------
-- vw_servicios_abiertos (vw_dias_atencion_servicio_centro)
-- Servicios abiertos ahora con centro, dirección y horario de cierre
-- Resultado esperado: se devuelve el listado con los servicios disponibles junto con su centro de salud, dirección y horario de cierre.
SELECT * FROM vw_servicios_abiertos;

-- -----------------------------------------------
-- vw_historial_internacion
-- Historial completo de internaciones ordenado por fecha ingreso
-- Resultado esperado: se listan todas las internaciones pasadas y activas ordenadas cronológicamente por su fecha de ingreso.
SELECT * FROM vw_historial_internacion;

-- -----------------------------------------------
-- vw_medico_mas_pacientes
-- Médico con más pacientes por centro, ordenado por barrio
-- Resultado esperado: se muestra de cada centro de salud el médico que más pacientes atendió, organizados por barrio.
SELECT * FROM vw_medico_mas_pacientes;

-- -----------------------------------------------
-- vw_top10_pacientes_ingresos
-- Top 10 pacientes con más ingresos en el último mes
-- Resultado esperado: se devuelven los 10 pacientes con la mayor cantidad de visitas e ingresos registrados en ese período.
SELECT * FROM vw_top10_pacientes_ingresos;

-- -----------------------------------------------
-- vw_historia_clinica_consolidada
-- Historia clínica consolidada: visitas, internaciones, centro y servicio más frecuentado, obra social
-- Resultado esperado: se devuelven los pacientes con sus métricas de atenciones, internaciones, centro más frecuentado, servicio más utilizado y su obra social.
SELECT * FROM vw_historia_clinica_consolidada;

-- Tests funciones

-- -----------------------------------------------
-- fnc_pacientes_por_diagnostico(p_diagnostico TEXT)
-- Retorna: ciudad_nombre, cantidad_pacientes

-- Test 1: Diagnóstico existente con pacientes en 3 ciudades
-- Diagnóstico único para test: "Test Bronquiolitis Aguda"
-- Resultado esperado: 3 filas, una por ciudad, con la cantidad correcta de cada una.
BEGIN;

-- Crear 3 ciudades en distintos departamentos
INSERT INTO departamento (id, nombre) OVERRIDING SYSTEM VALUE VALUES (9001, 'Depto Test A'), (9002, 'Depto Test B'), (9003, 'Depto Test C');
INSERT INTO ciudad (id, id_departamento, nombre) OVERRIDING SYSTEM VALUE VALUES (9001, 9001, 'Ciudad Test Alpha'), (9002, 9002, 'Ciudad Test Beta'), (9003, 9003, 'Ciudad Test Gamma');
INSERT INTO barrio (id, id_ciudad, nombre) OVERRIDING SYSTEM VALUE VALUES (9001, 9001, 'Barrio Test Alpha'), (9002, 9002, 'Barrio Test Beta'), (9003, 9003, 'Barrio Test Gamma');
INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura) OVERRIDING SYSTEM VALUE VALUES
    (9001, 9001, 'Centro Test Alpha', '2000-01-01', 'Calle A', 100),
    (9002, 9002, 'Centro Test Beta', '2000-01-01', 'Calle B', 200),
    (9003, 9003, 'Centro Test Gamma', '2000-01-01', 'Calle C', 300);
INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría Test', 1, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES
    (9001, 9001, 'Pediatría Test'),
    (9002, 9002, 'Pediatría Test'),
    (9003, 9003, 'Pediatría Test');
INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES
    ('991000001', 'Test', 'Medico1', '+549110000001', 'med1@test.com', '1980-01-01', 'Médico'),
    ('991000002', 'Test', 'Medico2', '+549110000002', 'med2@test.com', '1980-01-01', 'Médico'),
    ('991000003', 'Test', 'Medico3', '+549110000003', 'med3@test.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES
    (9001, '991000001'), (9002, '991000002'), (9003, '991000003');
INSERT INTO paciente (dni, nombre, apellido, nacimiento) VALUES
    (90000001, 'Paciente', 'Alpha1', '1990-01-01'),
    (90000002, 'Paciente', 'Alpha2', '1990-01-01'),
    (90000003, 'Paciente', 'Beta1', '1990-01-01'),
    (90000004, 'Paciente', 'Gamma1', '1990-01-01'),
    (90000005, 'Paciente', 'Gamma2', '1990-01-01');
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento) VALUES
    (9001, 90000001, '991000001', '2026-01-01', 'Test Bronquiolitis Aguda', 'Tratamiento'),
    (9001, 90000002, '991000001', '2026-01-02', 'Test Bronquiolitis Aguda', 'Tratamiento'),
    (9002, 90000003, '991000002', '2026-01-03', 'Test Bronquiolitis Aguda', 'Tratamiento'),
    (9003, 90000004, '991000003', '2026-01-04', 'Test Bronquiolitis Aguda', 'Tratamiento'),
    (9003, 90000005, '991000003', '2026-01-05', 'Test Bronquiolitis Aguda', 'Tratamiento');

SELECT * FROM fnc_pacientes_por_diagnostico('Test Bronquiolitis Aguda');

ROLLBACK;

-- Test 2: Diagnóstico que existe solo en una ciudad
-- Diagnóstico único para test: "Test Caídas Repetidas"
-- Resultado esperado: 1 fila con la cantidad de la ciudad correspondiente.
BEGIN;

INSERT INTO departamento (id, nombre) OVERRIDING SYSTEM VALUE VALUES (9010, 'Depto Test Solo');
INSERT INTO ciudad (id, id_departamento, nombre) OVERRIDING SYSTEM VALUE VALUES (9010, 9010, 'Ciudad Test Solo');
INSERT INTO barrio (id, id_ciudad, nombre) OVERRIDING SYSTEM VALUE VALUES (9010, 9010, 'Barrio Test Solo');
INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura) OVERRIDING SYSTEM VALUE VALUES
    (9010, 9010, 'Centro Test Solo', '2000-01-01', 'Calle Solo', 100);
INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Geriatría Test', 1, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (9010, 9010, 'Geriatría Test');
INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES
    ('991000010', 'Test', 'MedicoSolo', '+549110000010', 'medsolo@test.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (9010, '991000010');
INSERT INTO paciente (dni, nombre, apellido, nacimiento) VALUES
    (90000010, 'Paciente', 'Solo1', '1950-01-01'),
    (90000011, 'Paciente', 'Solo2', '1950-01-01');
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento) VALUES
    (9010, 90000010, '991000010', '2026-01-01', 'Test Caídas Repetidas', 'Tratamiento'),
    (9010, 90000011, '991000010', '2026-01-02', 'Test Caídas Repetidas', 'Tratamiento');

SELECT * FROM fnc_pacientes_por_diagnostico('Test Caídas Repetidas');

ROLLBACK;

-- Test 3: Diagnóstico con una ciudad que tiene 0 pacientes con ese diagnóstico
-- Diagnóstico "Oncología" (probablemente no hay)
-- Resultado esperado: la ciudad no aparece en el resultado (0 filas).
BEGIN;

SELECT * FROM fnc_pacientes_por_diagnostico('Oncología');

ROLLBACK;

-- -----------------------------------------------
-- fnc_servicios_disponibles(p_servicio VARCHAR, p_dia Dia, p_hora TIME)
-- Retorna: centro_nombre, centro_direccion, servicio_nombre, hora_apertura, hora_cierre

-- Test 1: Servicio abierto ahora en 2 centros
-- Tipo servicio único para test: "Pediatría General Test"
-- Usamos día/hora fijos para test determinista: Miércoles 10:00
-- Resultado esperado: aparecen los 2 centros.
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría General Test', 1, 1);
INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura) OVERRIDING SYSTEM VALUE VALUES
    (9101, 1, 'Centro Test Norte Santiago', '2000-01-01', 'Av. Norte', 100),
    (9102, 1, 'Centro Test Sur Santiago', '2000-01-01', 'Av. Sur', 200);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES
    (9101, 9101, 'Pediatría General Test'),
    (9102, 9102, 'Pediatría General Test');
INSERT INTO horario_atencion (id, apertura, cierre, dia) OVERRIDING SYSTEM VALUE VALUES
    (9101, '08:00', '14:00', 'Miércoles'),
    (9102, '09:00', '15:00', 'Miércoles');
INSERT INTO atencion_servicio (id_servicio, id_horario) VALUES
    (9101, 9101), (9102, 9102);

SELECT * FROM fnc_servicios_disponibles('Pediatría General Test', 'Miércoles', '10:00');

ROLLBACK;

-- -----------------------------------------------
-- fnc_servicios_disponibles - Caso 1: Servicio abierto ahora en 2 centros
-- Resultado esperado: 2 filas (Centro de Salud Norte y Centro de Salud Sur)
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 1, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría'), (1002, 2, 'Pediatría');
INSERT INTO horario_atencion (id, apertura, cierre, dia) OVERRIDING SYSTEM VALUE VALUES (1001, '11:00', '13:00', 'Lunes');
INSERT INTO atencion_servicio (id_servicio, id_horario) VALUES (1001, 1001), (1002, 1001);

SELECT * FROM fnc_servicios_disponibles('Pediatría', 'Lunes', '12:00');

ROLLBACK;

-- -----------------------------------------------
-- fnc_servicios_disponibles - Caso 2: El servicio existe en un centro pero fuera de horario
-- Resultado esperado: 0 filas (el centro no aparece)
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 1, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO horario_atencion (id, apertura, cierre, dia) OVERRIDING SYSTEM VALUE VALUES (1001, '09:00', '11:00', 'Lunes');
INSERT INTO atencion_servicio (id_servicio, id_horario) VALUES (1001, 1001);

SELECT * FROM fnc_servicios_disponibles('Pediatría', 'Lunes', '12:00');

ROLLBACK;

-- -----------------------------------------------
-- fnc_servicios_disponibles - Caso 3: Servicio que todavía no abrió hoy
-- Resultado esperado: 0 filas (el centro no aparece)
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 1, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO horario_atencion (id, apertura, cierre, dia) OVERRIDING SYSTEM VALUE VALUES (1001, '13:00', '15:00', 'Lunes');
INSERT INTO atencion_servicio (id_servicio, id_horario) VALUES (1001, 1001);

SELECT * FROM fnc_servicios_disponibles('Pediatría', 'Lunes', '12:00');

ROLLBACK;

-- -----------------------------------------------
-- fnc_medico_mas_pacientes_barrio - Caso 1: Un médico claramente por encima de los demás en un centro
-- Resultado esperado: 1 fila con Prueba Diez y 10 pacientes
BEGIN;

INSERT INTO barrio (id, id_ciudad, nombre) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Barrio Prueba A');
INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura) OVERRIDING SYSTEM VALUE VALUES (1001, 1001, 'Centro Prueba A1', '2000-01-01', 'Calle Prueba', 100);
INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 0, 3);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1001, 'Pediatría');

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES
    ('991000001', 'Prueba', 'Diez', '+5491100000001', 'diez@prueba.com', '1980-01-01', 'Médico'),
    ('991000002', 'Prueba', 'Seis', '+5491100000002', 'seis@prueba.com', '1980-01-01', 'Médico'),
    ('991000003', 'Prueba', 'Tres', '+5491100000003', 'tres@prueba.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (1001, '991000001'), (1001, '991000002'), (1001, '991000003');

INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', '2026-01-01', 'Prueba', 'Prueba' FROM paciente ORDER BY dni LIMIT 10;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000002', '2026-01-01', 'Prueba', 'Prueba' FROM paciente ORDER BY dni LIMIT 6;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000003', '2026-01-01', 'Prueba', 'Prueba' FROM paciente ORDER BY dni LIMIT 3;

SELECT * FROM fnc_medico_mas_pacientes_barrio() WHERE centro = 'Centro Prueba A1';

ROLLBACK;

-- -----------------------------------------------
-- fnc_medico_mas_pacientes_barrio - Caso 2: Resultado por cada centro de salud
-- Resultado esperado: 3 filas, una por centro, con su médico y cantidad
BEGIN;

INSERT INTO barrio (id, id_ciudad, nombre) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Barrio Prueba A');
INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 'Centro Prueba A1', '2000-01-01', 'Calle Prueba', 100),
    (1002, 1001, 'Centro Prueba A2', '2000-01-01', 'Calle Prueba', 200),
    (1003, 1001, 'Centro Prueba A3', '2000-01-01', 'Calle Prueba', 300);
INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 0, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 'Pediatría'),
    (1002, 1002, 'Pediatría'),
    (1003, 1003, 'Pediatría');

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES
    ('991000001', 'Prueba', 'Cinco', '+5491100000001', 'cinco@prueba.com', '1980-01-01', 'Médico'),
    ('991000002', 'Prueba', 'Tres', '+5491100000002', 'tres@prueba.com', '1980-01-01', 'Médico'),
    ('991000003', 'Prueba', 'Dos', '+5491100000003', 'dos@prueba.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (1001, '991000001'), (1002, '991000002'), (1003, '991000003');

INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', '2026-01-01', 'Prueba', 'Prueba' FROM paciente ORDER BY dni LIMIT 5;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1002, dni, '991000002', '2026-01-01', 'Prueba', 'Prueba' FROM paciente ORDER BY dni LIMIT 3;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1003, dni, '991000003', '2026-01-01', 'Prueba', 'Prueba' FROM paciente ORDER BY dni LIMIT 2;

SELECT * FROM fnc_medico_mas_pacientes_barrio() WHERE barrio = 'Barrio Prueba A';

ROLLBACK;

-- -----------------------------------------------
-- fnc_medico_mas_pacientes_barrio - Caso 3: Los resultados vienen agrupados por barrio
-- Resultado esperado: 3 filas, primero los 2 centros del Barrio Prueba A y luego el del Barrio Prueba B
BEGIN;

INSERT INTO barrio (id, id_ciudad, nombre) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Barrio Prueba A'), (1002, 1, 'Barrio Prueba B');
INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1002, 'Centro Prueba B1', '2000-01-01', 'Calle Prueba', 100),
    (1002, 1001, 'Centro Prueba A1', '2000-01-01', 'Calle Prueba', 200),
    (1003, 1001, 'Centro Prueba A2', '2000-01-01', 'Calle Prueba', 300);
INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 0, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 'Pediatría'),
    (1002, 1002, 'Pediatría'),
    (1003, 1003, 'Pediatría');

INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES
    ('991000001', 'Prueba', 'Tres', '+5491100000001', 'tres@prueba.com', '1980-01-01', 'Médico'),
    ('991000002', 'Prueba', 'Cuatro', '+5491100000002', 'cuatro@prueba.com', '1980-01-01', 'Médico'),
    ('991000003', 'Prueba', 'Dos', '+5491100000003', 'dos@prueba.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (1001, '991000001'), (1002, '991000002'), (1003, '991000003');

INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', '2026-01-01', 'Prueba', 'Prueba' FROM paciente ORDER BY dni LIMIT 3;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1002, dni, '991000002', '2026-01-01', 'Prueba', 'Prueba' FROM paciente ORDER BY dni LIMIT 4;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1003, dni, '991000003', '2026-01-01', 'Prueba', 'Prueba' FROM paciente ORDER BY dni LIMIT 2;

SELECT * FROM fnc_medico_mas_pacientes_barrio() WHERE barrio LIKE 'Barrio Prueba%';

ROLLBACK;

-- -----------------------------------------------
-- fnc_centro_mas_servicios - Caso 1: Un barrio con centros de distinta cantidad de servicios
-- Resultado esperado: 1 fila con Centro Prueba A1 y 5 servicios
BEGIN;

INSERT INTO barrio (id, id_ciudad, nombre) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Barrio Prueba A');
INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 'Centro Prueba A1', '2000-01-01', 'Calle Prueba', 100),
    (1002, 1001, 'Centro Prueba A2', '2000-01-01', 'Calle Prueba', 200),
    (1003, 1001, 'Centro Prueba A3', '2000-01-01', 'Calle Prueba', 300);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 'Cardiología'),
    (1002, 1001, 'Dermatología'),
    (1003, 1001, 'Geriatría'),
    (1004, 1001, 'Neurología'),
    (1005, 1001, 'Traumatología'),
    (1006, 1002, 'Cardiología'),
    (1007, 1002, 'Dermatología'),
    (1008, 1002, 'Geriatría'),
    (1009, 1003, 'Cardiología'),
    (1010, 1003, 'Dermatología');

SELECT * FROM fnc_centro_mas_servicios() WHERE barrio LIKE 'Barrio Prueba%';

ROLLBACK;

-- -----------------------------------------------
-- fnc_centro_mas_servicios - Caso 2: Un resultado por barrio
-- Resultado esperado: 3 filas, una por barrio, con el centro que más servicios tiene en cada uno
BEGIN;

INSERT INTO barrio (id, id_ciudad, nombre) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1, 'Barrio Prueba A'),
    (1002, 1, 'Barrio Prueba B'),
    (1003, 1, 'Barrio Prueba C');
INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 'Centro Prueba A1', '2000-01-01', 'Calle Prueba', 100),
    (1002, 1001, 'Centro Prueba A2', '2000-01-01', 'Calle Prueba', 200),
    (1003, 1002, 'Centro Prueba B1', '2000-01-01', 'Calle Prueba', 300),
    (1004, 1002, 'Centro Prueba B2', '2000-01-01', 'Calle Prueba', 400),
    (1005, 1003, 'Centro Prueba C1', '2000-01-01', 'Calle Prueba', 500),
    (1006, 1003, 'Centro Prueba C2', '2000-01-01', 'Calle Prueba', 600);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 'Cardiología'),
    (1002, 1001, 'Dermatología'),
    (1003, 1002, 'Cardiología'),
    (1004, 1003, 'Cardiología'),
    (1005, 1004, 'Cardiología'),
    (1006, 1004, 'Dermatología'),
    (1007, 1005, 'Cardiología'),
    (1008, 1005, 'Dermatología'),
    (1009, 1005, 'Geriatría'),
    (1010, 1006, 'Cardiología');

SELECT * FROM fnc_centro_mas_servicios() WHERE barrio LIKE 'Barrio Prueba%';

ROLLBACK;

-- -----------------------------------------------
-- fnc_centro_mas_servicios - Caso 3: Barrio con un único centro
-- Resultado esperado: 1 fila con Centro Prueba A1 y 3 servicios
BEGIN;

INSERT INTO barrio (id, id_ciudad, nombre) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Barrio Prueba A');
INSERT INTO centro_de_salud (id, id_barrio, nombre, inaguracion, calle, altura) OVERRIDING SYSTEM VALUE VALUES (1001, 1001, 'Centro Prueba A1', '2000-01-01', 'Calle Prueba', 100);

INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 'Cardiología'),
    (1002, 1001, 'Dermatología'),
    (1003, 1001, 'Geriatría');

SELECT * FROM fnc_centro_mas_servicios() WHERE barrio = 'Barrio Prueba A';

ROLLBACK;

-- -----------------------------------------------
-- fnc_pacientes_mas_ingresos - Caso 1: Hay más de 10 pacientes con ingresos en el último mes
-- Resultado esperado: exactamente 10 filas, ordenadas de mayor a menor cantidad de ingresos
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 0, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES ('991000001', 'Prueba', 'Medico', '+5491100000001', 'medico@prueba.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (1001, '991000001');

INSERT INTO paciente (dni, nombre, apellido, nacimiento) VALUES
    (90000001, 'Prueba', 'Uno', '1990-01-01'),
    (90000002, 'Prueba', 'Dos', '1990-01-01'),
    (90000003, 'Prueba', 'Tres', '1990-01-01'),
    (90000004, 'Prueba', 'Cuatro', '1990-01-01'),
    (90000005, 'Prueba', 'Cinco', '1990-01-01'),
    (90000006, 'Prueba', 'Seis', '1990-01-01'),
    (90000007, 'Prueba', 'Siete', '1990-01-01'),
    (90000008, 'Prueba', 'Ocho', '1990-01-01'),
    (90000009, 'Prueba', 'Nueve', '1990-01-01'),
    (90000010, 'Prueba', 'Diez', '1990-01-01'),
    (90000011, 'Prueba', 'Once', '1990-01-01'),
    (90000012, 'Prueba', 'Doce', '1990-01-01'),
    (90000013, 'Prueba', 'Trece', '1990-01-01'),
    (90000014, 'Prueba', 'Catorce', '1990-01-01'),
    (90000015, 'Prueba', 'Quince', '1990-01-01');

-- Los 15 pacientes tienen 4 ingresos recientes (el mismo INSERT repetido 4 veces)
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni > 90000000;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni > 90000000;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni > 90000000;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni > 90000000;

-- Los primeros 10 pacientes tienen un ingreso más
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni BETWEEN 90000001 AND 90000010;

-- Los primeros 5 pacientes tienen otro ingreso más
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni BETWEEN 90000001 AND 90000005;

SELECT * FROM fnc_pacientes_mas_ingresos();

ROLLBACK;

-- -----------------------------------------------
-- fnc_pacientes_mas_ingresos - Caso 2: Hay menos de 10 pacientes con ingresos
-- Resultado esperado: 4 filas (los pacientes de prueba), sin error
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 0, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES ('991000001', 'Prueba', 'Medico', '+5491100000001', 'medico@prueba.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (1001, '991000001');

INSERT INTO paciente (dni, nombre, apellido, nacimiento) VALUES
    (90000001, 'Prueba', 'Uno', '1990-01-01'),
    (90000002, 'Prueba', 'Dos', '1990-01-01'),
    (90000003, 'Prueba', 'Tres', '1990-01-01'),
    (90000004, 'Prueba', 'Cuatro', '1990-01-01');

-- Los 4 pacientes tienen 4 ingresos recientes (el mismo INSERT repetido 4 veces)
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni > 90000000;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni > 90000000;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni > 90000000;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni > 90000000;

-- Los primeros 2 pacientes tienen un ingreso más
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni BETWEEN 90000001 AND 90000002;

SELECT * FROM fnc_pacientes_mas_ingresos() WHERE dni > 90000000;

ROLLBACK;

-- -----------------------------------------------
-- fnc_pacientes_mas_ingresos - Caso 3: Ingresos anteriores al último mes
-- Resultado esperado: 1 fila con Prueba Uno y 4 ingresos (el de hace 40 días no se cuenta)
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 0, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES ('991000001', 'Prueba', 'Medico', '+5491100000001', 'medico@prueba.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (1001, '991000001');

INSERT INTO paciente (dni, nombre, apellido, nacimiento) VALUES (90000001, 'Prueba', 'Uno', '1990-01-01');

-- 4 ingresos recientes (el mismo INSERT repetido 4 veces)
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni = 90000001;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni = 90000001;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni = 90000001;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '5 days', 'Prueba', 'Prueba' FROM paciente WHERE dni = 90000001;

-- 1 ingreso de hace 40 días
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento)
SELECT 1001, dni, '991000001', CURRENT_DATE - INTERVAL '40 days', 'Prueba', 'Prueba' FROM paciente WHERE dni = 90000001;

SELECT * FROM fnc_pacientes_mas_ingresos() WHERE dni > 90000000;

ROLLBACK;

-- -----------------------------------------------
-- fnc_pacientes_internados_pocas_atenciones - Caso 1: Paciente internado con menos de 5 atenciones
-- Resultado esperado: 1 fila con Prueba Uno y 3 atenciones
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 0, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES ('991000001', 'Prueba', 'Medico', '+5491100000001', 'medico@prueba.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (1001, '991000001');

INSERT INTO paciente (dni, nombre, apellido, nacimiento) VALUES (90000001, 'Prueba', 'Uno', '1990-01-01');

INSERT INTO registro_hc (id, id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 90000001, '991000001', CURRENT_DATE - 30, 'Prueba', 'Prueba'),
    (1002, 1001, 90000001, '991000001', CURRENT_DATE - 20, 'Prueba', 'Prueba'),
    (1003, 1001, 90000001, '991000001', CURRENT_DATE - 10, 'Prueba', 'Prueba');

INSERT INTO internacion (id_registro_hc, fecha_ingreso, fecha_egreso) VALUES (1001, CURRENT_DATE - 30, NULL);

SELECT * FROM fnc_pacientes_internados_pocas_atenciones() WHERE dni = 90000001;

ROLLBACK;

-- -----------------------------------------------
-- fnc_pacientes_internados_pocas_atenciones - Caso 2: Paciente con exactamente 5 atenciones
-- Resultado esperado: 0 filas (el paciente no se cuenta)
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 0, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES ('991000001', 'Prueba', 'Medico', '+5491100000001', 'medico@prueba.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (1001, '991000001');

INSERT INTO paciente (dni, nombre, apellido, nacimiento) VALUES (90000001, 'Prueba', 'Uno', '1990-01-01');

INSERT INTO registro_hc (id, id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 90000001, '991000001', CURRENT_DATE - 50, 'Prueba', 'Prueba'),
    (1002, 1001, 90000001, '991000001', CURRENT_DATE - 40, 'Prueba', 'Prueba'),
    (1003, 1001, 90000001, '991000001', CURRENT_DATE - 30, 'Prueba', 'Prueba'),
    (1004, 1001, 90000001, '991000001', CURRENT_DATE - 20, 'Prueba', 'Prueba'),
    (1005, 1001, 90000001, '991000001', CURRENT_DATE - 10, 'Prueba', 'Prueba');

INSERT INTO internacion (id_registro_hc, fecha_ingreso, fecha_egreso) VALUES (1001, CURRENT_DATE - 50, NULL);

SELECT * FROM fnc_pacientes_internados_pocas_atenciones() WHERE dni = 90000001;

ROLLBACK;

-- -----------------------------------------------
-- fnc_pacientes_internados_pocas_atenciones - Caso 3: Paciente internado sin ninguna atención
-- Resultado real de la implementación: 1 fila con 0 atenciones
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 0, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO personal (matricula, nombre, apellido, telefono, email, nacimiento, rol) VALUES ('991000001', 'Prueba', 'Medico', '+5491100000001', 'medico@prueba.com', '1980-01-01', 'Médico');
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (1001, '991000001');

INSERT INTO paciente (dni, nombre, apellido, nacimiento) VALUES (90000001, 'Prueba', 'Uno', '1990-01-01');

INSERT INTO registro_hc (id, id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento) OVERRIDING SYSTEM VALUE VALUES
    (1001, 1001, 90000001, '991000001', CURRENT_DATE - 240, 'Prueba', 'Prueba');

INSERT INTO internacion (id_registro_hc, fecha_ingreso, fecha_egreso) VALUES (1001, CURRENT_DATE - 240, NULL);

SELECT * FROM fnc_pacientes_internados_pocas_atenciones() WHERE dni = 90000001;

ROLLBACK;

-- Tests usuarios

-- -----------------------------------------------
-- Usuario administrador - Base: Crear y modificar la estructura de una tabla
-- Resultado esperado: todas las instrucciones se ejecutan sin error de permisos
BEGIN;
SET ROLE administrador;

-- Datos del rol
SELECT current_user, rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user;

-- Crear una tabla
CREATE TABLE prueba_admin (id INT PRIMARY KEY, nombre VARCHAR(30));

-- Modificar la estructura de la tabla creada y de una tabla existente
ALTER TABLE prueba_admin ADD COLUMN observacion TEXT;
ALTER TABLE tipo_servicio ADD COLUMN prueba INT;

-- Comprobar que los cambios se aplicaron
SELECT table_name, column_name FROM information_schema.columns
WHERE (table_name = 'prueba_admin' AND column_name = 'observacion') OR (table_name = 'tipo_servicio' AND column_name = 'prueba');

ROLLBACK;

-- Comprobar que no quedó nada
SELECT to_regclass('prueba_admin') AS tabla_prueba;

-- -----------------------------------------------
-- Usuario personal - Base: Consultar la historia clínica de un paciente y la lista de servicios
-- Resultado esperado: ambas consultas se ejecutan correctamente y devuelven datos
BEGIN;
SET ROLE personal;

-- Historia clínica de un paciente
SELECT id, id_servicio, matricula_personal, dia_visita, diagnostico, tratamiento FROM registro_hc WHERE dni_paciente = 16183162 ORDER BY dia_visita;

-- Lista de servicios
SELECT id, id_centro_salud, nombre_tipo_servicio FROM servicio ORDER BY id;

ROLLBACK;

-- -----------------------------------------------
-- Usuario personal - Excepción: Consultar los datos de contacto del resto del personal
-- Resultado esperado: la consulta no devuelve los datos del resto del personal (resultado filtrado)
BEGIN;
SET ROLE personal;

-- Listado con los datos de contacto del personal
SELECT matricula, nombre, apellido, telefono, email FROM personal;

-- Cantidad de filas visibles
SELECT count(*) AS cantidad_personal FROM personal;

ROLLBACK;

-- -----------------------------------------------

-- Usuario paciente - Base: Consultar los centros de salud disponibles
-- Resultado esperado: la consulta se ejecuta correctamente y devuelve los centros de salud
BEGIN;
SET ROLE paciente;

SELECT id, nombre, calle, altura FROM centro_de_salud ORDER BY id;

ROLLBACK;

-- -----------------------------------------------
-- Usuario paciente - Excepción: Insertar un registro de atención o modificar una tabla
-- Resultado esperado: el motor bloquea las tres operaciones con error de falta de privilegios

-- Intento 1: insertar un registro de atención
BEGIN;
SET ROLE paciente;
INSERT INTO registro_hc (id_servicio, dni_paciente, matricula_personal, dia_visita, diagnostico, tratamiento) VALUES (1, 16183162, '541023799881', CURRENT_DATE, 'Prueba', 'Prueba');
ROLLBACK;

-- Intento 2: modificar los datos de una tabla
BEGIN;
SET ROLE paciente;
UPDATE centro_de_salud SET nombre = 'Centro modificado' WHERE id = 1;
ROLLBACK;

-- Intento 3: modificar la estructura (crear una tabla)
BEGIN;
SET ROLE paciente;
CREATE TABLE prueba_paciente (id INT);
ROLLBACK;

-- Comprobar que no se modificó nada
SELECT to_regclass('prueba_paciente') AS tabla_prueba, nombre FROM centro_de_salud WHERE id = 1;
