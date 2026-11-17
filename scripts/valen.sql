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