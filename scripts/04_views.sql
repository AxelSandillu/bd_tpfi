-- Vista: vw_servicios_abiertos
-- Descripción: Lista con los servicios abiertos en el momento de la consulta, mostrando a qué centro pertenece, su dirección y horario de cierre.

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

-- Vista: vw_historial_internacion
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

-- Vista: vw_medico_mas_pacientes
-- Descripción: Muestra el médico de cada centro de salud que más pacientes tuvo y la cantidad correspondiente, organizados por barrio. Utiliza la función con la misma descripción.

CREATE OR REPLACE VIEW vw_medico_mas_pacientes AS
WITH pacientes_por_medico AS (
      SELECT b.nombre AS barrio, cs.id AS id_centro, cs.nombre AS centro,
            p.nombre AS nombre_medico, p.apellido AS apellido_medico,
            COUNT(DISTINCT hc.dni_paciente) AS cantidad_pacientes
      FROM registro_hc hc
      JOIN servicio s ON hc.id_servicio = s.id
      JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
      JOIN barrio b ON cs.id_barrio = b.id
      JOIN personal p ON hc.matricula_personal = p.matricula
      WHERE p.rol = 'Médico'
      GROUP BY b.nombre, cs.id, cs.nombre, p.matricula, p.nombre, p.apellido
)
SELECT barrio, centro, nombre_medico, apellido_medico, cantidad_pacientes
FROM pacientes_por_medico ppm
WHERE cantidad_pacientes = (
      SELECT MAX(ppm2.cantidad_pacientes)
      FROM pacientes_por_medico ppm2
      WHERE ppm2.id_centro = ppm.id_centro
)
ORDER BY barrio, centro;


-- Vista: vw_top10_pacientes_ingresos
-- Descripción: Muestra los 10 pacientes con mayor cantidad de ingresos en centros de salud en el último mes. Utiliza la función con la misma descripción.

CREATE OR REPLACE VIEW vw_top10_pacientes_ingresos AS
SELECT pa.dni, pa.nombre, pa.apellido,
      COUNT(i.id) AS cantidad_ingresos
FROM internacion i
JOIN registro_hc hc ON i.id_registro_hc = hc.id
JOIN paciente pa ON hc.dni_paciente = pa.dni
WHERE i.fecha_ingreso >= CURRENT_DATE - INTERVAL '1 month'
GROUP BY pa.dni, pa.nombre, pa.apellido
ORDER BY cantidad_ingresos DESC
LIMIT 10;

-- Vista: vw_historia_clinica_consolidada
-- Descripción: Muestra cada paciente con su historia clínica, mostrando cantidad de internaciones, cantidad de visitas, centro de salud más frecuentado, servicio más usado, obra social (si tiene).
CREATE OR REPLACE VIEW vw_historia_clinica_consolidada AS
SELECT
    p.dni AS dni,
    (
        -- Cantidad de visitas del paciente
        SELECT COUNT(*)
        FROM registro_hc r
        WHERE r.dni_paciente = p.dni
    ) AS cant_visitas,
    (
        -- Cantidad histórica de internaciones del paciente
        SELECT COUNT(*)
        FROM internacion i
        JOIN registro_hc r ON r.id = i.id_registro_hc
        WHERE r.dni_paciente = p.dni
    ) AS cant_internaciones,
    (
        -- Centro de salud más frecuentado
        SELECT c.nombre
        FROM registro_hc r
        JOIN servicio s ON s.id = r.id_servicio
        JOIN centro_de_salud c ON c.id = s.id_centro_salud
        WHERE r.dni_paciente = p.dni
        GROUP BY c.nombre
        ORDER BY COUNT(*) DESC
        LIMIT 1
    ) AS centro_mas_visitado,
    (
        -- Tipo de servicio más utilizado
        SELECT s.nombre_tipo_servicio
        FROM registro_hc r
        JOIN servicio s ON s.id = r.id_servicio
        WHERE r.dni_paciente = p.dni
        GROUP BY s.nombre_tipo_servicio
        ORDER BY COUNT(*) DESC
        LIMIT 1
    ) AS servicio_mas_usado,
    o.razon_social AS obra_social
FROM paciente p
LEFT JOIN obra_social o ON o.id = p.id_obra_social;