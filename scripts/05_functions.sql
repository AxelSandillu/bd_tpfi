-- Función: fnc_pacientes_por_diagnostico
-- Descripción: Muestra la cantidad de pacientes con el diagnóstico especificado de cada ciudad.

CREATE OR REPLACE FUNCTION fnc_pacientes_por_diagnostico(p_diagnostico TEXT)
RETURNS TABLE (
      ciudad_nombre      VARCHAR,
      cantidad_pacientes BIGINT
)
LANGUAGE sql
AS $$
      SELECT ci.nombre, COUNT(DISTINCT hc.dni_paciente)
      FROM registro_hc hc
      JOIN servicio s ON hc.id_servicio = s.id
      JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
      JOIN barrio b ON cs.id_barrio = b.id
      JOIN ciudad ci ON b.id_ciudad = ci.id
      WHERE hc.diagnostico = p_diagnostico
      GROUP BY ci.nombre
      ORDER BY ci.nombre;
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
LANGUAGE sql
AS $$
      SELECT cs.nombre, cs.direccion, ts.nombre, h.apertura, h.cierre
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
$$;

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

-- Función: fn_pacientes_mas_ingresos
-- Descripción: Muestra los 10 pacientes con mayor cantidad de ingresos en centros de salud en el último mes.

CREATE OR REPLACE FUNCTION fn_pacientes_mas_ingresos()
RETURNS TABLE (
    dni INT,
    paciente VARCHAR(61),
    cant_ingresos BIGINT,
    centro_mas_visitado VARCHAR(30)
) AS $$
BEGIN
    RETURN QUERY
    WITH ingresos_mes AS (
        SELECT 
            pa.dni,
            cs.nombre AS nom_centro,
            ROW_NUMBER() OVER (PARTITION BY pa.dni ORDER BY COUNT(*) DESC) as rn
        FROM registro_hc rhc
        JOIN paciente pa ON rhc.dni_paciente = pa.dni
        JOIN servicio s ON rhc.id_servicio = s.id
        JOIN centro_de_salud cs ON s.id_centro_salud = cs.id
        WHERE rhc.dia_visita >= (CURRENT_TIMESTAMP - INTERVAL '1 month')
        GROUP BY pa.dni, cs.nombre
    ),
    total_ingresos AS (
        SELECT 
            rhc.dni_paciente AS dni,
            COUNT(*) AS total
        FROM registro_hc rhc
        WHERE rhc.dia_visita >= (CURRENT_TIMESTAMP - INTERVAL '1 month')
        GROUP BY rhc.dni_paciente
    )
    SELECT 
        ti.dni,
        CONCAT(p.nombre, ' ', p.apellido) AS paciente,
        ti.total AS cant_ingresos,
        im.nom_centro AS centro_mas_visitado
    FROM total_ingresos ti
    JOIN paciente p ON ti.dni = p.dni
    JOIN ingresos_mes im ON ti.dni = im.dni AND im.rn = 1
    ORDER BY ti.total DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Función: fn_pacientes_internados_pocas_atenciones
-- Descripción: Muestra la cantidad de pacientes con menos de 5 atenciones en los últimos 6 meses que se encuentren actualmente internados en algún centro.

CREATE OR REPLACE FUNCTION fn_pacientes_internados_pocas_atenciones()
RETURNS TABLE (
    dni INT,
    paciente VARCHAR(61),
    cant_atenciones_6_meses BIGINT,
    id_internacion INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.dni,
        CONCAT(p.nombre, ' ', p.apellido) AS paciente,
        (
            -- Subconsulta para contar las atenciones reales del paciente en los últimos 6 meses
            SELECT COUNT(r.id) 
            FROM registro_hc r 
            WHERE r.dni_paciente = p.dni 
              AND r.dia_visita >= (CURRENT_TIMESTAMP - INTERVAL '6 month')
        ) AS cant_atenciones_6_meses,
        i.id AS id_internacion
    FROM internacion i
    JOIN registro_hc rhc_ingreso ON i.id_registro_hc = rhc_ingreso.id
    JOIN paciente p ON rhc_ingreso.dni_paciente = p.dni
    WHERE i.fecha_egreso IS NULL -- Filtra los que se encuentran actualmente internados
      AND p.dni IN (
          -- Filtra aquellos pacientes que en total tienen menos de 5 atenciones en los últimos 6 meses
          SELECT pac.dni
          FROM paciente pac
          LEFT JOIN registro_hc r ON pac.dni = r.dni_paciente AND r.dia_visita >= (CURRENT_TIMESTAMP - INTERVAL '6 month')
          GROUP BY pac.dni
          HAVING COUNT(r.id) < 5
      );
END;
$$ LANGUAGE plpgsql;