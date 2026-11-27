-- Test: fnc_servicios_disponibles - Caso 1: Servicio abierto ahora en 2 centros
-- Resultado esperado: 2 filas (Centro de Salud Norte y Centro de Salud Sur)
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 1, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría'), (1002, 2, 'Pediatría');
INSERT INTO horario_atencion (id, apertura, cierre, dia) OVERRIDING SYSTEM VALUE VALUES (1001, '11:00', '13:00', 'Lunes');
INSERT INTO atencion_servicio (id_servicio, id_horario) VALUES (1001, 1001), (1002, 1001);

SELECT * FROM fnc_servicios_disponibles('Pediatría', 'Lunes', '12:00');

ROLLBACK;

-- Test: fnc_servicios_disponibles - Caso 2: El servicio existe en un centro pero fuera de horario
-- Resultado esperado: 0 filas (el centro no aparece)
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 1, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO horario_atencion (id, apertura, cierre, dia) OVERRIDING SYSTEM VALUE VALUES (1001, '09:00', '11:00', 'Lunes');
INSERT INTO atencion_servicio (id_servicio, id_horario) VALUES (1001, 1001);

SELECT * FROM fnc_servicios_disponibles('Pediatría', 'Lunes', '12:00');

ROLLBACK;

-- Test: fnc_servicios_disponibles - Caso 3: Servicio que todavía no abrió hoy
-- Resultado esperado: 0 filas (el centro no aparece)
BEGIN;

INSERT INTO tipo_servicio (nombre, num_enfermeros, num_medicos) VALUES ('Pediatría', 1, 1);
INSERT INTO servicio (id, id_centro_salud, nombre_tipo_servicio) OVERRIDING SYSTEM VALUE VALUES (1001, 1, 'Pediatría');
INSERT INTO horario_atencion (id, apertura, cierre, dia) OVERRIDING SYSTEM VALUE VALUES (1001, '13:00', '15:00', 'Lunes');
INSERT INTO atencion_servicio (id_servicio, id_horario) VALUES (1001, 1001);

SELECT * FROM fnc_servicios_disponibles('Pediatría', 'Lunes', '12:00');

ROLLBACK;

-- Test: fnc_medico_mas_pacientes_barrio - Caso 1: Un médico claramente por encima de los demás en un centro
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

-- Test: fnc_medico_mas_pacientes_barrio - Caso 2: Resultado por cada centro de salud
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

-- Test: fnc_medico_mas_pacientes_barrio - Caso 3: Los resultados vienen agrupados por barrio
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

-- Test: fnc_centro_mas_servicios - Caso 1: Un barrio con centros de distinta cantidad de servicios
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

-- Test: fnc_centro_mas_servicios - Caso 2: Un resultado por barrio
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

-- Test: fnc_centro_mas_servicios - Caso 3: Barrio con un único centro
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

-- Test: fnc_pacientes_mas_ingresos - Caso 1: Hay más de 10 pacientes con ingresos en el último mes
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

-- Test: fnc_pacientes_mas_ingresos - Caso 2: Hay menos de 10 pacientes con ingresos
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

-- Test: fnc_pacientes_mas_ingresos - Caso 3: Ingresos anteriores al último mes
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

-- Test: fnc_pacientes_internados_pocas_atenciones - Caso 1: Paciente internado con menos de 5 atenciones
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

-- Test: fnc_pacientes_internados_pocas_atenciones - Caso 2: Paciente con exactamente 5 atenciones
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

-- Test: fnc_pacientes_internados_pocas_atenciones - Caso 3: Paciente internado sin ninguna atención
-- Resultado esperado según el Excel: 0 filas (no se cuenta)
-- Resultado real de la implementación: 1 fila con 0 atenciones (ver observaciones)
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

-- Test: Usuario administrador - Base: Crear y modificar la estructura de una tabla
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

-- Test: Usuario personal - Base: Consultar la historia clínica de un paciente y la lista de servicios
-- Resultado esperado: ambas consultas se ejecutan correctamente y devuelven datos
BEGIN;
SET ROLE personal;

-- Historia clínica de un paciente
SELECT id, id_servicio, matricula_personal, dia_visita, diagnostico, tratamiento FROM registro_hc WHERE dni_paciente = 16183162 ORDER BY dia_visita;

-- Lista de servicios
SELECT id, id_centro_salud, nombre_tipo_servicio FROM servicio ORDER BY id;

ROLLBACK;

-- Test: Usuario personal - Excepción: Consultar los datos de contacto del resto del personal
-- Resultado esperado: la consulta no devuelve los datos del resto del personal (resultado filtrado)
BEGIN;
SET ROLE personal;

-- Listado con los datos de contacto del personal
SELECT matricula, nombre, apellido, telefono, email FROM personal;

-- Cantidad de filas visibles
SELECT count(*) AS cantidad_personal FROM personal;

ROLLBACK;

-- Test: Usuario paciente - Base: Consultar los centros de salud disponibles
-- Resultado esperado: la consulta se ejecuta correctamente y devuelve los centros de salud
BEGIN;
SET ROLE paciente;

SELECT id, nombre, calle, altura FROM centro_de_salud ORDER BY id;

ROLLBACK;

-- Test: Usuario paciente - Excepción: Insertar un registro de atención o modificar una tabla
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