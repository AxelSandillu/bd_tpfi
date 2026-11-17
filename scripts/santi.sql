-- Función: fn_medico_mas_pacientes_barrio
-- Descripción: Muestra el médico que más pacientes tuvo y cantidad de pacientes por cada centro de salud, organizados por barrio.
CREATE OR REPLACE FUNCTION fn_medico_mas_pacientes_barrio () RETURNS TABLE (
  barrio VARCHAR(30),
  centro VARCHAR(30),
  medico VARCHAR(61),
  cant_pacientes INT
) AS $$
    SELECT DISTINCT ON (b.id, cs.id)
        b.nombre AS barrio,
        cs.nombre AS centro,
        p.nombre || ' ' || p.apellido AS medico,
        COUNT(DISTINCT rhc.dni_paciente) AS cant_pacientes
    FROM registro_hc rhc
    JOIN personal p ON rhc.matricula_personal = p.matricula
    JOIN servicio s ON rhc.id_servicio = s.id
    JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
    JOIN barrio b ON cs.id_barrio = b.id
    WHERE p.rol = 'Médico'
    GROUP BY b.id, b.nombre, cs.id, cs.nombre, p.matricula, p.nombre, p.apellido
    ORDER BY b.id, cs.id, COUNT(DISTINCT rhc.dni_paciente) DESC;
$$ LANGUAGE sql;

-- Función: fn_centro_mas_servicios
-- Descripción: Muestra el centro de salud con mayor cantidad de servicios de cada barrio.
CREATE OR REPLACE FUNCTION fn_centro_mas_servicios () RETURNS TABLE (
  barrio VARCHAR(30),
  centro VARCHAR(30),
  cant_servicios INT
) AS $$
    SELECT DISTINCT ON (b.id)
        b.nombre AS barrio,
        cs.nombre AS centro,
        COUNT(s.id) AS cant_servicios
    FROM servicio s
    JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
    JOIN barrio b ON cs.id_barrio = b.id
    GROUP BY b.id, b.nombre, cs.id, cs.nombre
    ORDER BY b.id, COUNT(s.id) DESC;
$$ LANGUAGE sql;