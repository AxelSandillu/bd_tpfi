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