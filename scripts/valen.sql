-- Triggers: trg_servicio_personal_encargado
-- Descripción: Verifica que el personal a cargo sea un médico.

CREATE OR REPLACE FUNCTION fnc_servicio_personal_encargado() RETURNS TRIGGER AS $$
LANGUAGE plpgsql
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

CREATE TRIGGER trg_servicio_personal_encargado
BEFORE INSERT OR UPDATE ON servicio
FOR EACH ROW
EXECUTE FUNCTION fnc_servicio_personal_encargado();

-- Triggers: trg_servicio_centro_unico
-- Descripción: Verifica que en cada centro de salud no haya más de un servicio de un mismo tipo.

CREATE OR REPLACE FUNCTION fnc_servicio_centro_unico() RETURNS TRIGGER AS $$
LANGUAGE plpgsql
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

CREATE TRIGGER trg_servicio_centro_unico
BEFORE INSERT OR UPDATE ON servicio
FOR EACH ROW
EXECUTE FUNCTION fnc_servicio_centro_unico();


-- Triggers: trg_registro_hc_encargado
-- Descripción: Verifica que el medico que lo atendió trabaje en el servicio utilizado y sea un medico.

CREATE OR REPLACE FUNCTION fnc_registro_hc_encargado() RETURNS TRIGGER AS $$
LANGUAGE plpgsql
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

CREATE TRIGGER trg_registro_hc_encargado
BEFORE INSERT OR UPDATE ON registro_hc
FOR EACH ROW
EXECUTE FUNCTION fnc_registro_hc_encargado();

-- Triggers: trg_internacion_ingreso
-- Descripción: La fecha de ingreso debe coincidir con la fecha cargada en el registro.

CREATE OR REPLACE FUNCTION fnc_internacion_ingreso() RETURNS TRIGGER AS $$
LANGUAGE plpgsql
BEGIN
      IF NEW.fecha_ingreso <> (SELECT fecha FROM registro_hc WHERE id_registro = NEW.id_registro) THEN
            RAISE EXCEPTION 'La fecha de ingreso debe coincidir con la fecha del registro';
      END IF;

      RETURN NEW;
END;
$$;

CREATE TRIGGER trg_internacion_ingreso
BEFORE INSERT OR UPDATE ON internacion
FOR EACH ROW
EXECUTE FUNCTION fnc_internacion_ingreso();