-- Tests triggers

-- -----------------------------------------------
-- trg_internacion_ingreso

-- Excepción: fecha ingreso distinta a registro HC
-- registro_hc id=1 tiene dia_visita='2026-11-17'
INSERT INTO internacion (id_registro_hc, fecha_ingreso, fecha_egreso) VALUES (1, '2026-11-18', NULL);

-- -----------------------------------------------
-- trg_internacion_egreso

-- Base: actualizar internación sin egreso con fecha posterior
-- internacion id=107 tiene fecha_ingreso='2026-11-05', fecha_egreso=NULL
UPDATE internacion SET fecha_egreso = '2026-11-10' WHERE id = 107;

-- Excepción: actualizar internación sin egreso con fecha anterior
-- internacion id=108 tiene fecha_ingreso='2026-11-05', fecha_egreso=NULL
UPDATE internacion SET fecha_egreso = '2026-11-04' WHERE id = 108;

-- -----------------------------------------------
-- trg_personal_servicio_max_personal

-- Base: agregar enfermero a servicio con cupo
-- servicio 60 (Pediatría general, max 2 enfermeros, actual 0 enfermeros)
-- enfermero 541026060241 (Elisa Caballero) tiene Pediatría, NO está en personal_servicio
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (60, '541026060241');

-- Excepción: agregar médico a servicio sin cupo
-- servicio 8 (Medicina General, max 1 médico, actual 1 médico: 541016446866)
-- médico 541018990279 (Yunnuel Arevalo) tiene Medicina General, NO está en personal_servicio
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (8, '541018990279');

-- -----------------------------------------------
-- trg_personal_servicio_especialidad

-- Base: agregar enfermero CON especialidades requeridas
-- servicio 30 (Neurología, max 2 enfermeros, actual 0 enfermeros) requiere Neurología
-- enfermero 541038950382 (Luis Bravo) tiene Neurología, NO está en personal_servicio
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (30, '541038950382');

-- Excepción: agregar enfermero SIN especialidades requeridas
-- servicio 30 (Neurología) requiere Neurología
-- enfermero 541026060241 (Elisa Caballero) tiene Pediatría, NO tiene Neurología, NO está en personal_servicio
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (30, '541026060241');

-- -----------------------------------------------
-- trg_personal_servicio_superposición

-- Base: agregar enfermero a servicio SIN superposición
-- enfermero 541021704836 (Nelly Leyva) está en servicio 10 (Pediatría general)
-- servicio 10 horarios: Miércoles 08-12, Domingo 10-18, Sábado 15-21
-- servicio 66 (Pediatría general) horarios: Martes 18-23, Domingo 18-23 (límite 18 no superpone con 10-18)
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (66, '541021704836');

-- Excepción: agregar enfermero a servicio CON superposición
-- mismo enfermero 541021704836 en servicio 10
-- servicio 68 (Pediatría general) horarios: Martes 10-18, Sábado 14-20
-- Superposición con servicio 10 en Sábado (15-21 vs 14-20)
INSERT INTO personal_servicio (id_servicio, matricula_personal) VALUES (68, '541021704836');

-- Tests vistas

-- -----------------------------------------------
-- vw_servicios_abiertos (vw_dias_atencion_servicio_centro)
-- Servicios abiertos ahora con centro, dirección y horario de cierre
SELECT * FROM vw_servicios_abiertos;

-- -----------------------------------------------
-- vw_historial_internacion
-- Historial completo de internaciones ordenado por fecha ingreso
SELECT * FROM vw_historial_internacion;

-- -----------------------------------------------
-- vw_medico_mas_pacientes
-- Médico con más pacientes por centro, ordenado por barrio
SELECT * FROM vw_medico_mas_pacientes;

-- -----------------------------------------------
-- vw_top10_pacientes_ingresos
-- Top 10 pacientes con más ingresos en el último mes
SELECT * FROM vw_top10_pacientes_ingresos;

-- -----------------------------------------------
-- vw_historia_clinica_consolidada
-- Historia clínica consolidada: visitas, internaciones, centro y servicio más frecuentado, obra social
SELECT * FROM vw_historia_clinica_consolidada;

-- Tests funciones

-- -----------------------------------------------
-- fnc_pacientes_por_diagnostico(p_diagnostico TEXT)
-- Retorna: ciudad_nombre, cantidad_pacientes

-- Test 1: Diagnóstico existente con pacientes en 3 ciudades
-- Diagnóstico "Bronquiolitis aguda" aparece en varias ciudades
SELECT * FROM fnc_pacientes_por_diagnostico('Bronquiolitis aguda');

-- Test 2: Diagnóstico que existe solo en una ciudad
-- Diagnóstico "Caídas repetidas" 
SELECT * FROM fnc_pacientes_por_diagnostico('Caídas repetidas');

-- Test 3: Diagnóstico con una ciudad que tiene 0 pacientes con ese diagnóstico
-- Diagnóstico "Oncología" (probablemente no hay)
SELECT * FROM fnc_pacientes_por_diagnostico('Oncología');

-- -----------------------------------------------
-- fnc_servicios_disponibles(p_servicio VARCHAR, p_dia Dia, p_hora TIME)
-- Retorna: centro_nombre, centro_direccion, servicio_nombre, hora_apertura, hora_cierre

-- Test 1: Servicio abierto ahora en 2 centros
-- 'Pediatría general' con horario vigente en 2 centros (día/hora actual)
-- Cast CURRENT_TIME a TIME (sin time zone) porque la función espera TIME
SELECT * FROM fnc_servicios_disponibles(
    'Pediatría general',
    CASE EXTRACT(ISODOW FROM CURRENT_TIMESTAMP)
        WHEN 1 THEN 'Lunes'::Dia WHEN 2 THEN 'Martes'::Dia WHEN 3 THEN 'Miércoles'::Dia
        WHEN 4 THEN 'Jueves'::Dia WHEN 5 THEN 'Viernes'::Dia WHEN 6 THEN 'Sábado'::Dia
        WHEN 7 THEN 'Domingo'::Dia END,
    CURRENT_TIME::TIME
);