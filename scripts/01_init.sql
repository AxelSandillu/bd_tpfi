-- Enum: Día
CREATE TYPE Dia AS ENUM(
  'Lunes',
  'Martes',
  'Miércoles',
  'Jueves',
  'Viernes',
  'Sábado',
  'Domingo'
);

-- Enum: Rol
CREATE TYPE Rol AS ENUM('Médico', 'Enfermero');

-- Domain: Matricula
CREATE DOMAIN Matricula AS VARCHAR CHECK (VALUE ~ '^[0-9]{2}[1-5][0-9]+$');

-- Tabla: Departamento
CREATE TABLE IF NOT EXISTS departamento (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre VARCHAR(30) NOT NULL UNIQUE
);

-- Tabla: Ciudad
CREATE TABLE IF NOT EXISTS ciudad (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_departamento INT NOT NULL,
  nombre VARCHAR(30) NOT NULL UNIQUE,
  FOREIGN KEY (id_departamento) REFERENCES departamento
);

-- Tabla: Barrio
CREATE TABLE IF NOT EXISTS barrio (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_ciudad INT NOT NULL,
  nombre VARCHAR(30) NOT NULL UNIQUE,
  FOREIGN KEY (id_ciudad) REFERENCES ciudad
);

-- Tabla: Obra social
CREATE TABLE IF NOT EXISTS obra_social (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  razon_social VARCHAR(30) NOT NULL,
  estado BOOLEAN NOT NULL
);

-- Tabla: Paciente
CREATE TABLE IF NOT EXISTS paciente (
  dni INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_obra_social INT,
  nombre VARCHAR(30) NOT NULL,
  apellido VARCHAR(30) NOT NULL,
  nacimiento TIMESTAMP NOT NULL,
  num_asociado INT UNIQUE,
  FOREIGN KEY (id_obra_social) REFERENCES obra_social
);

-- Tabla: Centro de salud
CREATE TABLE IF NOT EXISTS centro_de_salud (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_barrio INT NOT NULL,
  nombre VARCHAR(30) NOT NULL UNIQUE,
  direccion VARCHAR(30) NOT NULL,
  inaguracion TIMESTAMP NOT NULL,
  calle VARCHAR(30) NOT NULL,
  altura INT NOT NULL,
  FOREIGN KEY (id_barrio) REFERENCES barrio
);

-- Tabla: Tipo de servicio
CREATE TABLE IF NOT EXISTS tipo_servicio (
  nombre VARCHAR(30) NOT NULL,
  num_enfermeros INT NOT NULL,
  num_medicos INT NOT NULL,
  PRIMARY KEY (nombre)
);

-- Tabla: Personal
CREATE TABLE IF NOT EXISTS personal (
  matricula Matricula NOT NULL UNIQUE,
  nombre VARCHAR(30) NOT NULL,
  apellido VARCHAR(30) NOT NULL,
  telefono VARCHAR(30) NOT NULL UNIQUE,
  email VARCHAR(30) NOT NULL UNIQUE,
  nacimiento TIMESTAMP NOT NULL,
  rol Rol NOT NULL,
  PRIMARY KEY (matricula)
);

-- Tabla: Servicio
CREATE TABLE IF NOT EXISTS servicio (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_centro_salud INT NOT NULL,
  nombre_tipo_servicio VARCHAR(30) NOT NULL,
  matricula_encargado Matricula,
  FOREIGN KEY (id_centro_salud) REFERENCES centro_de_salud,
  FOREIGN KEY (nombre_tipo_servicio) REFERENCES tipo_servicio,
  FOREIGN KEY (matricula_encargado) REFERENCES personal
);

-- Tabla: Personal servicio
CREATE TABLE IF NOT EXISTS personal_servicio (
  id_servicio INT NOT NULL,
  matricula_personal Matricula NOT NULL UNIQUE,
  PRIMARY KEY (id_servicio, matricula_personal),
  FOREIGN KEY (id_servicio) REFERENCES servicio,
  FOREIGN KEY (matricula_personal) REFERENCES personal
);

-- Tabla: Registro historial clinico
CREATE TABLE IF NOT EXISTS registro_hc (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_servicio INT NOT NULL,
  dni_paciente INT NOT NULL,
  matricula_personal Matricula NOT NULL,
  dia_visita TIMESTAMP NOT NULL,
  diagnostico TEXT NOT NULL,
  tratamiento TEXT NOT NULL,
  FOREIGN KEY (id_servicio) REFERENCES servicio,
  FOREIGN KEY (dni_paciente) REFERENCES paciente,
  FOREIGN KEY (matricula_personal) REFERENCES personal
);

-- Tabla: Internación
CREATE TABLE IF NOT EXISTS internacion (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_registro_hc INT NOT NULL,
  fecha_ingreso TIMESTAMP NOT NULL,
  fecha_egreso TIMESTAMP,
  FOREIGN KEY (id_registro_hc) REFERENCES registro_hc
);

-- Tabla: Especialidad
CREATE TABLE especialidad (nombre VARCHAR(30) NOT NULL, PRIMARY KEY (nombre));

-- Tabla: Especializado en
CREATE TABLE especializado_en (
  matricula_personal Matricula NOT NULL,
  nombre_especialidad VARCHAR(30) NOT NULL,
  PRIMARY KEY (matricula_personal, nombre_especialidad),
  FOREIGN KEY (matricula_personal) REFERENCES personal (matricula),
  FOREIGN KEY (nombre_especialidad) REFERENCES especialidad (nombre)
);

-- Tabla: Especialidad requerida
CREATE TABLE especialidad_requerida (
  nombre_tipo_servicio VARCHAR(30) NOT NULL,
  nombre_especialidad VARCHAR(30) NOT NULL,
  PRIMARY KEY (nombre_tipo_servicio, nombre_especialidad),
  FOREIGN KEY (nombre_tipo_servicio) REFERENCES tipo_servicio (nombre),
  FOREIGN KEY (nombre_especialidad) REFERENCES especialidad (nombre)
);

-- Tabla: Horario atención
CREATE TABLE horario_atencion (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  apertura TIME NOT NULL,
  cierre TIME NOT NULL,
  dia DIA NOT NULL
);

-- Tabla: Atención centro
CREATE TABLE atencion_centro (
  id_centro_salud INT NOT NULL,
  id_horario INT NOT NULL,
  PRIMARY KEY (id_centro_salud, id_horario),
  FOREIGN KEY (id_centro_salud) REFERENCES centro_de_salud (id),
  FOREIGN KEY (id_horario) REFERENCES horario_atencion (id)
);

-- Tabla: Atención servicio
CREATE TABLE atencion_servicio (
  id_servicio INT NOT NULL,
  id_horario INT NOT NULL,
  PRIMARY KEY (id_servicio, id_horario),
  FOREIGN KEY (id_servicio) REFERENCES servicio (id),
  FOREIGN KEY (id_horario) REFERENCES horario_atencion (id)
);