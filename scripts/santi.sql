-- Trigger: Inaguración del centro de salúd.
-- Descripción:
-- Verifica que la fecha de inauguración sea anterior a hoy
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
-- Descripción:
-- Verifica que la fecha de nacimiento sea anterior a  hoy
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
-- Descripción:
-- Verifica que la fecha de nacimiento sea anterior a hoy.
CREATE TRIGGER trg_personal_nacimiento BEFORE INSERT
OR
UPDATE ON personal FOR EACH ROW
EXECUTE FUNCTION fnc_nacimiento ();

-- Trigger: Validar datos de personal.
-- Descripción:
-- Verifica que el telefono, email y edad sean validos.
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