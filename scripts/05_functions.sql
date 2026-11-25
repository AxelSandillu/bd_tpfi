-- Función: fnc_pacientes_por_diagnostico
-- Descripción: Muestra la cantidad de pacientes con el diagnóstico especificado de cada ciudad.

CREATE OR REPLACE FUNCTION fnc_pacientes_por_diagnostico(p_diagnostico TEXT)
RETURNS TABLE (
      ciudad_nombre      VARCHAR,
      cantidad_pacientes BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
      RETURN QUERY
      SELECT ci.nombre,
            COUNT(DISTINCT hc.dni_paciente)
      FROM registro_hc hc
      JOIN servicio s ON hc.id_servicio = s.id
      JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
      JOIN barrio b ON cs.id_barrio = b.id
      JOIN ciudad ci ON b.id_ciudad = ci.id
      WHERE hc.diagnostico = p_diagnostico
      GROUP BY ci.nombre
      ORDER BY ci.nombre;
END;
$$;


-- Función: fnc_servicios_disponibles
-- Descripción: Muestra los centros de salud que cuenten con el servicio especificado y que el mismo esté abierto en el momento de la consulta.

CREATE OR REPLACE FUNCTION fnc_servicios_disponibles(p_servicio VARCHAR, p_dia Dia, p_hora TIME)
RETURNS TABLE (
      centro_nombre    VARCHAR,
      centro_direccion VARCHAR,
      servicio_nombre  VARCHAR,
      hora_apertura    TIME,
      hora_cierre      TIME
)
LANGUAGE plpgsql
AS $$
BEGIN
      RETURN QUERY
      SELECT cs.nombre,
            cs.direccion,
            ts.nombre,
            h.apertura,
            h.cierre
      FROM servicio s
      JOIN tipo_servicio ts ON s.nombre_tipo_servicio = ts.nombre
      JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
      JOIN atencion_servicio a ON a.id_servicio = s.id
      JOIN horario_atencion h ON a.id_horario = h.id
      WHERE ts.nombre = p_servicio
            AND h.dia = p_dia
            AND h.apertura <= p_hora
            AND h.cierre >= p_hora
      ORDER BY cs.nombre;
END;
$$;


-- Función: fnc_medico_mas_pacientes_barrio
-- Descripción: Muestra el médico que más pacientes tuvo y cantidad de pacientes por cada centro de salud, organizados por barrio.

CREATE OR REPLACE FUNCTION fnc_medico_mas_pacientes_barrio()
RETURNS TABLE (
      barrio         VARCHAR,
      centro         VARCHAR,
      medico         VARCHAR,
      cant_pacientes BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
      RETURN QUERY
      SELECT DISTINCT ON (b.id, cs.id)
            b.nombre AS barrio,
            cs.nombre AS centro,
            CONCAT(p.nombre, ' ', p.apellido)::varchar AS medico,
            COUNT(DISTINCT rhc.dni_paciente) AS cant_pacientes
      FROM registro_hc rhc
      JOIN personal p ON rhc.matricula_personal = p.matricula
      JOIN servicio s ON rhc.id_servicio = s.id
      JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
      JOIN barrio b ON cs.id_barrio = b.id
      WHERE p.rol = 'Médico'
      GROUP BY b.id, b.nombre, cs.id, cs.nombre, p.matricula, p.nombre, p.apellido
      ORDER BY b.id, cs.id, COUNT(DISTINCT rhc.dni_paciente) DESC, p.apellido, p.nombre;
END;
$$;


-- Función: fnc_centro_mas_servicios
-- Descripción: Muestra el centro de salud con mayor cantidad de servicios de cada barrio.

CREATE OR REPLACE FUNCTION fnc_centro_mas_servicios()
RETURNS TABLE (
      barrio         VARCHAR,
      centro         VARCHAR,
      cant_servicios BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
      RETURN QUERY
      SELECT DISTINCT ON (b.id)
            b.nombre AS barrio,
            cs.nombre AS centro,
            COUNT(s.id) AS cant_servicios
      FROM servicio s
      JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
      JOIN barrio b ON cs.id_barrio = b.id
      GROUP BY b.id, b.nombre, cs.id, cs.nombre
      ORDER BY b.id, COUNT(s.id) DESC, cs.nombre;
END;
$$;


-- Función: fnc_pacientes_mas_ingresos
-- Descripción: Muestra los 10 pacientes con mayor cantidad de ingresos en centros de salud en el último mes.

CREATE OR REPLACE FUNCTION fnc_pacientes_mas_ingresos()
RETURNS TABLE (
      dni                 INT,
      paciente            VARCHAR,
      cant_ingresos       BIGINT,
      centro_mas_visitado VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
      RETURN QUERY
      SELECT p.dni,
            CONCAT(p.nombre, ' ', p.apellido)::varchar AS paciente,
            COUNT(rhc.id) AS cant_ingresos,
            (
                  SELECT cs.nombre
                  FROM registro_hc rhc_centro
                  JOIN servicio s ON rhc_centro.id_servicio = s.id
                  JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
                  WHERE rhc_centro.dni_paciente = p.dni
                    AND rhc_centro.dia_visita >= (CURRENT_TIMESTAMP - INTERVAL '1 month')
                  GROUP BY cs.nombre
                  ORDER BY COUNT(*) DESC, cs.nombre ASC
                  LIMIT 1
            ) AS centro_mas_visitado
      FROM registro_hc rhc
      JOIN paciente p ON rhc.dni_paciente = p.dni
      WHERE rhc.dia_visita >= (CURRENT_TIMESTAMP - INTERVAL '1 month')
      GROUP BY p.dni, p.nombre, p.apellido
      ORDER BY cant_ingresos DESC, p.dni ASC
      LIMIT 10;
END;
$$;


-- Función: fnc_pacientes_internados_pocas_atenciones
-- Descripción: Muestra los pacientes actualmente internados que registran menos de 5 atenciones en los últimos 6 meses.

CREATE OR REPLACE FUNCTION fnc_pacientes_internados_pocas_atenciones()
RETURNS TABLE (
      dni                    INT,
      paciente               VARCHAR,
      cant_atenciones_6_meses BIGINT,
      id_internacion         INT
)
LANGUAGE plpgsql
AS $$
BEGIN
      RETURN QUERY
      SELECT p.dni,
            CONCAT(p.nombre, ' ', p.apellido) AS paciente,
            (
                  SELECT COUNT(r.id)
                  FROM registro_hc r
                  WHERE r.dni_paciente = p.dni
                    AND r.dia_visita >= (CURRENT_TIMESTAMP - INTERVAL '6 month')
            ) AS cant_atenciones_6_meses,
            i.id AS id_internacion
      FROM internacion i
      JOIN registro_hc rhc_ingreso ON i.id_registro_hc = rhc_ingreso.id
      JOIN paciente p ON rhc_ingreso.dni_paciente = p.dni
      WHERE i.fecha_egreso IS NULL
        AND p.dni IN (
              SELECT pac.dni
              FROM paciente pac
              LEFT JOIN registro_hc r
                ON pac.dni = r.dni_paciente
              AND r.dia_visita >= (CURRENT_TIMESTAMP - INTERVAL '6 month')
              GROUP BY pac.dni
              HAVING COUNT(r.id) < 5
        );
END;
$$;