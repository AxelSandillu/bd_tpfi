
-- 1. TRIGGER: trg_personal_servicio_max_personal
-- Descripción: Verifica que no se pase de la cantidad máxima de médicos y enfermeros según su tipo de servicio.

CREATE OR REPLACE FUNCTION func_personal_servicio_max_personal() RETURNS TRIGGER AS $$
DECLARE
    v_rol Rol;
    v_max_medicos INT;
    v_max_enfermeros INT;
    v_cant_actual INT;
BEGIN
    -- Obtener el rol del personal que se quiere insertar
    SELECT rol INTO v_rol FROM personal WHERE matricula = NEW.matricula_personal;
    
    -- Obtener los máximos requeridos por el tipo de servicio asociado al servicio
    SELECT ts.num_medicos, ts.num_enfermeros 
    INTO v_max_medicos, v_max_enfermeros
    FROM servicio s
    JOIN tipo_servicio ts ON s.nombre_tipo_servicio = ts.nombre
    WHERE s.id = NEW.id_servicio;
    
    IF v_rol = 'Médico' THEN
        SELECT COUNT(*) INTO v_cant_actual
        FROM personal_servicio ps
        JOIN personal p ON ps.matricula_personal = p.matricula
        WHERE ps.id_servicio = NEW.id_servicio AND p.rol = 'Médico';
        
        IF v_cant_actual >= v_max_medicos THEN
            RAISE EXCEPTION 'El servicio ya tiene la cantidad máxima de médicos requerida por su tipo. No hay cupo para ese rol.';
        END IF;
        
    ELSIF v_rol = 'Enfermero' THEN
        SELECT COUNT(*) INTO v_cant_actual
        FROM personal_servicio ps
        JOIN personal p ON ps.matricula_personal = p.matricula
        WHERE ps.id_servicio = NEW.id_servicio AND p.rol = 'Enfermero';
        
        IF v_cant_actual >= v_max_enfermeros THEN
            RAISE EXCEPTION 'El servicio ya tiene la cantidad máxima de enfermeros requerida por su tipo. No hay cupo para ese rol.';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_personal_servicio_max_personal
BEFORE INSERT ON personal_servicio
FOR EACH ROW EXECUTE PROCEDURE func_personal_servicio_max_personal();




-- 2. TRIGGER: trg_personal_servicio_especialidad
-- Descripción: Verifica que todo el personal tenga las especialidades requeridas para el servicio.

CREATE OR REPLACE FUNCTION func_personal_servicio_especialidad() RETURNS TRIGGER AS $$
DECLARE
    v_esp_faltante VARCHAR(30);
BEGIN
    -- Verificar si existen especialidades requeridas por el tipo de servicio que el personal NO posea
    SELECT er.nombre_especialidad INTO v_esp_faltante
    FROM servicio s
    JOIN especialidad_requerida er ON s.nombre_tipo_servicio = er.nombre_tipo_servicio
    WHERE s.id = NEW.id_servicio
      AND er.nombre_especialidad NOT IN (
          SELECT nombre_especialidad 
          FROM especializado_en 
          WHERE matricula_personal = NEW.matricula_personal
      )
    LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION 'La persona no tiene la especialidad requerida: %. Se impide el insert.', v_esp_faltante;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_personal_servicio_especialidad
BEFORE INSERT ON personal_servicio
FOR EACH ROW EXECUTE PROCEDURE func_personal_servicio_especialidad();




-- 3. TRIGGER: trg_personal_servicio_superposición
-- Descripción: Verifica que un mismo miembro del personal no trabaje en varios servicios en el mismo horario.

CREATE OR REPLACE FUNCTION func_personal_servicio_superposicion() RETURNS TRIGGER AS $$
DECLARE
    v_conflicto INT;
BEGIN
    -- Verifica si el personal ya está asignado a otro servicio cuyo horario de atención se superpone
    SELECT COUNT(*) INTO v_conflicto
    FROM personal_servicio ps1
    JOIN atencion_servicio as1 ON ps1.id_servicio = as1.id_servicio
    JOIN horario_atencion h1 ON as1.id_horario = h1.id
    -- Horario del nuevo servicio que se quiere asignar
    JOIN atencion_servicio as_nuevo ON NEW.id_servicio = as_nuevo.id_servicio
    JOIN horario_atencion h_nuevo ON as_nuevo.id_horario = h_nuevo.id
    WHERE ps1.matricula_personal = NEW.matricula_personal
      AND h1.dia = h_nuevo.dia
      -- Condición de superposición de horas (apertura/cierre)
      AND (h1.apertura < h_nuevo.cierre AND h1.cierre > h_nuevo.apertura);

    IF v_conflicto > 0 THEN
        RAISE EXCEPTION 'La persona ya trabaja en otro servicio en un horario que se superpone. Se impide el insert.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_personal_servicio_superposición
BEFORE INSERT ON personal_servicio
FOR EACH ROW EXECUTE PROCEDURE func_personal_servicio_superposicion();




-- 4. TRIGGER: trg_internacion_ingreso
-- Descripción: La fecha de ingreso debe coincidir con la fecha cargada en el registro de historia clínica asociado.

CREATE OR REPLACE FUNCTION func_internacion_ingreso() RETURNS TRIGGER AS $$
DECLARE
    v_fecha_visita TIMESTAMP;
BEGIN
    -- Obtener la fecha de la visita del registro de historia clínica asociado
    SELECT dia_visita INTO v_fecha_visita
    FROM registro_hc
    WHERE id = NEW.id_registro_hc;

    -- Verificar coincidencia
    IF NEW.fecha_ingreso <> v_fecha_visita THEN
        RAISE EXCEPTION 'La fecha de ingreso no coincide con la fecha cargada en el registro de historia clínica asociado.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_internacion_ingreso
BEFORE INSERT OR UPDATE ON internacion
FOR EACH ROW EXECUTE PROCEDURE func_internacion_ingreso();