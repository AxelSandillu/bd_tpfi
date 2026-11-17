-- Trigger: Inaguración del centro de salúd.
-- Descripción: Verifica que la fecha de inauguración sea anterior a hoy
CREATE OR REPLACE FUNCTION fnc_centro_de_salud_inauguracion () RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
      IF NEW.inaguracion >= CURRENT_DATE THEN
            RAISE EXCEPTION 'La fecha de inaguración debe ser estrictamente anterior a hoy (%)', CURRENT_DATE;
      END IF;
    
      RETURN NEW; 
END;
$$;

CREATE TRIGGER trg_centro_de_salud_inauguracion BEFORE INSERT
OR
UPDATE ON centro_de_salud FOR EACH ROW
EXECUTE FUNCTION fnc_centro_de_salud_inauguracion ();

-- Trigger: Fecha de naciminto del paciente.
-- Descripción: Verifica que la fecha de nacimiento sea anterior a  hoy
CREATE OR REPLACE FUNCTION fnc_nacimiento () RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
      IF NEW.nacimiento >= CURRENT_DATE THEN
            RAISE EXCEPTION 'La fecha de nacimineto del paciente debe ser anterior a la actual (%)', CURRENT_DATE;
      END IF;
  
      RETURN NEW;
END;
$$;

CREATE TRIGGER trg_paciente_nacimiento BEFORE INSERT
OR
UPDATE ON paciente FOR EACH ROW
EXECUTE FUNCTION fnc_nacimiento ();

-- Trigger: Nacimiento del personal
-- Descripción: Verifica que la fecha de nacimiento sea anterior a hoy.
CREATE TRIGGER trg_personal_nacimiento BEFORE INSERT
OR
UPDATE ON personal FOR EACH ROW
EXECUTE FUNCTION fnc_nacimiento ();

-- Trigger: Validar datos de personal.
-- Descripción: Verifica que el telefono, email y edad sean validos.
CREATE OR REPLACE FUNCTION fnc_personal_validar_datos () RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
      -- 1. Validar formato de email
      IF NEW.email IS NULL OR NEW.email !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$' THEN
            RAISE EXCEPTION 'Formato de email inválido: %', COALESCE(NEW.email, 'NULL');
      END IF;

      -- 2. Validar teléfono (máximo 15 caracteres según VARCHAR(15) y mínimo 7 dígitos reales)
      IF NEW.telefono IS NULL 
            OR NEW.telefono !~ '^\+?[0-9\s\-\(\)]{7,15}$' 
            OR LENGTH(REGEXP_REPLACE(NEW.telefono, '[^0-9]', '', 'g')) < 7 THEN
            RAISE EXCEPTION 'Formato de teléfono inválido: %', COALESCE(NEW.telefono, 'NULL');
      END IF;

      -- 3. Validar mayoría de edad (18 años cumplidos)
      IF NEW.nacimiento IS NULL OR AGE(CURRENT_DATE, NEW.nacimiento) < INTERVAL '18 years' THEN
            RAISE EXCEPTION 'La persona debe ser mayor de 18 años (nacimiento: %)', COALESCE(NEW.nacimiento::TEXT, 'NULL');
      END IF;
END;
$$;

CREATE TRIGGER trg_personal_validar_datos BEFORE INSERT
OR
UPDATE ON personal FOR EACH ROW
EXECUTE FUNCTION fnc_personal_validar_datos ();

-- Trigger: trg_servicio_personal_encargado
-- Descripción: Verifica que el personal a cargo sea un médico.
CREATE OR REPLACE FUNCTION fnc_servicio_personal_encargado () RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
      IF NOT EXISTS (
            SELECT 1
            FROM personal
            WHERE personal.id_personal = NEW.id_personal
              AND personal.tipo_personal = 'Médico'
      ) THEN
            RAISE EXCEPTION 'El personal encargado debe ser un médico';
      END IF;

      RETURN NEW;
END;
$$;

CREATE TRIGGER trg_servicio_personal_encargado BEFORE INSERT
OR
UPDATE ON servicio FOR EACH ROW
EXECUTE FUNCTION fnc_servicio_personal_encargado ();

-- Trigger: trg_servicio_centro_unico
-- Descripción: Verifica que en cada centro de salud no haya más de un servicio de un mismo tipo.
CREATE OR REPLACE FUNCTION fnc_servicio_centro_unico () RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
      IF EXISTS (
            SELECT 1
            FROM servicio
            WHERE servicio.id_centro = NEW.id_centro AND servicio.tipo_servicio = NEW.tipo_servicio AND servicio.id_servicio <> NEW.id_servicio
      ) THEN
            RAISE EXCEPTION 'Ya existe un servicio de este tipo en el centro de salud';
      END IF;

      RETURN NEW;
END;
$$;

CREATE TRIGGER trg_servicio_centro_unico BEFORE INSERT
OR
UPDATE ON servicio FOR EACH ROW
EXECUTE FUNCTION fnc_servicio_centro_unico ();

-- Trigger: trg_registro_hc_encargado
-- Descripción: Verifica que el medico que lo atendió trabaje en el servicio utilizado y sea un medico.
CREATE OR REPLACE FUNCTION fnc_registro_hc_encargado () RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
      IF NOT EXISTS (
            SELECT 1
            FROM personal
            WHERE personal.id_personal = NEW.id_personal
              AND personal.tipo_personal = 'Médico'
              AND personal.id_servicio = NEW.id_servicio
      ) THEN
            RAISE EXCEPTION 'El personal encargado debe ser un médico que trabaje en el servicio utilizado';
      END IF;
END;
$$;

CREATE TRIGGER trg_registro_hc_encargado BEFORE INSERT
OR
UPDATE ON registro_hc FOR EACH ROW
EXECUTE FUNCTION fnc_registro_hc_encargado ();

-- Trigger: trg_internacion_ingreso
-- Descripción: La fecha de ingreso debe coincidir con la fecha cargada en el registro.
CREATE OR REPLACE FUNCTION fnc_internacion_ingreso () RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
      IF NEW.fecha_ingreso <> (SELECT fecha FROM registro_hc WHERE id_registro = NEW.id_registro) THEN
            RAISE EXCEPTION 'La fecha de ingreso debe coincidir con la fecha del registro';
      END IF;

      RETURN NEW;
END;
$$;

CREATE TRIGGER trg_internacion_ingreso BEFORE INSERT
OR
UPDATE ON internacion FOR EACH ROW
EXECUTE FUNCTION fnc_internacion_ingreso ();

-- Trigger: trg_internacion_egreso
-- Descripción: La fecha de egreso debe ser posterior  a la de ingreso.
CREATE OR REPLACE FUNCTION fnc_internacion_ingreso () RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
      IF NEW.fecha_ingreso <=  NEW.fecha_egreso THEN
            RAISE EXCEPTION 'La fecha de egreso no puede ser anterior a la de ingreso';
      END IF;

      RETURN NEW;
END;
$$;

CREATE TRIGGER trg_internacion_ingreso BEFORE INSERT
OR
UPDATE ON internacion FOR EACH ROW
EXECUTE FUNCTION fnc_internacion_ingreso ();

-- TRIGGER: trg_personal_servicio_max_personal
-- Descripción: Verifica que no se pase de la cantidad máxima de médicos y enfermeros según su tipo de servicio.
CREATE OR REPLACE FUNCTION fnc_personal_servicio_max_personal () RETURNS TRIGGER AS $$
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

CREATE TRIGGER trg_personal_servicio_max_personal BEFORE INSERT ON personal_servicio FOR EACH ROW
EXECUTE PROCEDURE fnc_personal_servicio_max_personal ();

-- TRIGGER: trg_personal_servicio_especialidad
-- Descripción: Verifica que todo el personal tenga las especialidades requeridas para el servicio.
CREATE OR REPLACE FUNCTION fnc_personal_servicio_especialidad () RETURNS TRIGGER AS $$
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

CREATE TRIGGER trg_personal_servicio_especialidad BEFORE INSERT ON personal_servicio FOR EACH ROW
EXECUTE PROCEDURE fnc_personal_servicio_especialidad ();

-- TRIGGER: trg_personal_servicio_superposición
-- Descripción: Verifica que un mismo miembro del personal no trabaje en varios servicios en el mismo horario.
CREATE OR REPLACE FUNCTION fnc_personal_servicio_superposicion () RETURNS TRIGGER AS $$
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

CREATE TRIGGER trg_personal_servicio_superposición BEFORE INSERT ON personal_servicio FOR EACH ROW
EXECUTE PROCEDURE fnc_personal_servicio_superposicion ();