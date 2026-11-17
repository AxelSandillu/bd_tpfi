-- Vista: vw_historia_clinica_consolidada
-- Descripción: Muestra cada paciente con su historia clínica, mostrando cantidad de internaciones, cantidad de visitas, centro de salud más frecuentado, servicio más usado, obra social (si tiene).
CREATE VIEW vw_historia_clinica_consolidada AS
SELECT
  p.dni AS DNI,
  (
    -- Contar la cantidad de visitas
    SELECT
      COUNT(*)
    FROM
      registro_hc r
    WHERE
      r.dni_paciente = p.dni
  ) AS cant_visitas,
  (
    -- Contar la cantidad de internaciones historiacas
    SELECT
      COUNT(*)
    FROM
      internacion i
      JOIN registro_hc r ON r.id = i.id_registro_hc
    WHERE
      r.dni_paciente = p.dni
  ) AS cant_internaciones,
  (
    -- Busca el centro mas usado
    SELECT
      c.nombre
    FROM
      registro_hc r
      JOIN servicio s ON s.id = r.id_servicio
      JOIN centro_de_salud c ON c.id = s.id_centro_salud
    WHERE
      r.dni_paciente = p.dni
    GROUP BY
      c.nombre
    ORDER BY
      COUNT(*) DESC
    LIMIT
      1
  ) AS centro_mas_visitado,
  (
    -- Busca el servicio mas usado
    SELECT
      s.nombre_tipo_servicio
    FROM
      registro_hc r
      JOIN servicio s ON s.id = r.id_servicio
    WHERE
      r.dni_paciente = p.dni
    GROUP BY
      s.nombre_tipo_servicio
    ORDER BY
      COUNT(*) DESC
    LIMIT
      1
  ) AS servicio_mas_usado,
  o.razon_social AS obra_social
FROM
  paciente p
  LEFT JOIN obra_social o ON o.id = p.id_obra_social;