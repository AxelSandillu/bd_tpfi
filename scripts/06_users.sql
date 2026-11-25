-- Crear roles
CREATE ROLE administrador WITH LOGIN PASSWORD 'admin_2026' SUPERUSER CREATEDB CREATEROLE;
CREATE ROLE personal WITH LOGIN PASSWORD 'personal_2026' NOSUPERUSER;
CREATE ROLE paciente WITH LOGIN PASSWORD 'paciente_2026' NOSUPERUSER;

-- Uso del schema public
GRANT USAGE ON SCHEMA public TO personal;
GRANT USAGE ON SCHEMA public TO paciente;

-- Permitir ver todo a personal
GRANT SELECT ON ALL TABLES IN SCHEMA public TO personal;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO personal;

-- Permitir inserción de registros e internaciones a personal
GRANT INSERT ON registro_hc TO personal;
GRANT INSERT ON internacion TO personal;
GRANT USAGE, SELECT ON SEQUENCE registro_hc_id_seq TO personal;
GRANT USAGE, SELECT ON SEQUENCE internacion_id_seq TO personal;

-- Permitir edición de teléfono y email propio a personal
GRANT UPDATE (telefono, email) ON personal TO personal;

-- Permitir uso de funciones a personal
GRANT EXECUTE ON FUNCTION fnc_medico_mas_pacientes_barrio() TO personal;
GRANT EXECUTE ON FUNCTION fnc_centro_mas_servicios() TO personal;
GRANT EXECUTE ON FUNCTION fnc_pacientes_por_diagnostico(TEXT) TO personal;
GRANT EXECUTE ON FUNCTION fnc_servicios_disponibles(VARCHAR, Dia, TIME) TO personal;
GRANT EXECUTE ON FUNCTION fnc_pacientes_mas_ingresos() TO personal;
GRANT EXECUTE ON FUNCTION fnc_pacientes_internados_pocas_atenciones() TO personal;

-- Permitir ver tablas maestras a paciente
GRANT SELECT ON centro_de_salud, servicio, tipo_servicio, obra_social, departamento, ciudad, barrio TO paciente;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO paciente;
GRANT SELECT ON registro_hc TO paciente;
GRANT SELECT ON internacion TO paciente;

-- Seguridad a nivel de fila en personal
ALTER TABLE personal ENABLE ROW LEVEL SECURITY;
CREATE POLICY personal_ver_propios ON personal FOR SELECT TO personal USING (matricula = current_user);
CREATE POLICY personal_editar_propios ON personal FOR UPDATE TO personal USING (matricula = current_user) WITH CHECK (matricula = current_user);

-- Seguridad a nivel de fila en paciente
ALTER TABLE paciente ENABLE ROW LEVEL SECURITY;
CREATE POLICY paciente_ver_propios ON paciente FOR SELECT TO paciente USING (dni = current_user::int);
CREATE POLICY paciente_ver_registros_propios ON registro_hc FOR SELECT TO paciente USING (dni_paciente = current_user::int);
CREATE POLICY paciente_ver_internaciones_propios ON internacion FOR SELECT TO paciente USING (
  id_registro_hc IN (SELECT id FROM registro_hc WHERE dni_paciente = current_user::int)
);
