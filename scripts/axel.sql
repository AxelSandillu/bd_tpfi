
-- 1. Vista: vw_servicios_abiertos
-- Descripción: Lista con los servicios abiertos en el momento de la consulta, 
-- mostrando a qué centro pertenece, su dirección y horario de cierre.

CREATE OR REPLACE VIEW vw_servicios_abiertos AS
SELECT 
    s.id AS ID_servicio,
    s.nombre_tipo_servicio AS servicio,
    cs.nombre AS centro,
    ha.cierre AS cierre,
    d.nombre AS depto,
    c.nombre AS ciudad,
    b.nombre AS barrio,
    cs.altura AS altura
FROM servicio s
JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
JOIN barrio b ON cs.id_barrio = b.id
JOIN ciudad c ON b.id_ciudad = c.id
JOIN departamento d ON c.id_departamento = d.id
JOIN atencion_servicio aserv ON s.id = aserv.id_servicio
JOIN horario_atencion ha ON aserv.id_horario = ha.id
WHERE ha.dia = CASE EXTRACT(ISODOW FROM CURRENT_TIMESTAMP)
    WHEN 1 THEN 'Lunes'::Dia
    WHEN 2 THEN 'Martes'::Dia
    WHEN 3 THEN 'Miércoles'::Dia
    WHEN 4 THEN 'Jueves'::Dia
    WHEN 5 THEN 'Viernes'::Dia
    WHEN 6 THEN 'Sábado'::Dia
    WHEN 7 THEN 'Domingo'::Dia
END
AND CURRENT_TIME BETWEEN ha.apertura AND ha.cierre;



-- 2. Vista: vw_historial_internacion
-- Descripción: Seguimiento de todas las internaciones históricas y actuales, 
-- ordenadas por fecha de ingreso.

CREATE OR REPLACE VIEW vw_historial_internacion AS
SELECT 
    i.id AS ID_internacion,
    rhc.dni_paciente AS DNI,
    i.fecha_ingreso AS fecha_ingreso,
    i.fecha_egreso AS fecha_egreso,
    -- Cálculo del tiempo de estadía en días (o cadena de texto legible)
    CASE 
        WHEN i.fecha_egreso IS NOT NULL THEN CONCAT(EXTRACT(DAY FROM (i.fecha_egreso - i.fecha_ingreso)), ' días')
        ELSE 'En curso'
    END AS tiempo_estadia,
    CONCAT(p.nombre, ' ', p.apellido) AS responsable,
    cs.nombre AS centro
FROM internacion i
JOIN registro_hc rhc ON i.id_registro_hc = rhc.id
JOIN servicio s ON rhc.id_servicio = s.id
JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
JOIN personal p ON rhc.matricula_personal = p.matricula
ORDER BY i.fecha_ingreso ASC;