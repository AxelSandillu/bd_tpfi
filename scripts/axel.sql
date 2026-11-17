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