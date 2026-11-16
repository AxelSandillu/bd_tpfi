-- Tabla internacion
CREATE TABLE IF NOT EXISTS internacion (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_registro_hc INT NOT NULL,
  fecha_ingreso DATETIME NOT NULL,
  fecha_egreso DATETIME,
  FOREIGN KEY (id_registro_hc) REFERENCES registro_hc
);

-- Tabla registro_hc
CREATE TABLE IF NOT EXISTS registro_hc (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_servicio INT NOT NULL,
  dni_paciente INT NOT NULL,
  matricula_personal VARCHAR(30) NOT NULL,
  dia_visita DATETIME NOT NULL,
  diagnostico TEXT NOT NULL,
  tratamiento TEXT NOT NULL,
  FOREIGN KEY (id_servicio) REFERENCES servicio,
  FOREIGN KEY (dni_paciente) REFERENCES paciente,
  FOREIGN KEY (matricula_personal) REFERENCES personal
);

-- Tabla tipo_servicio
CREATE TABLE IF NOT EXISTS tipo_servicio (
  nombre VARCHAR(30) NOT NULL,
  num_enfermeros INT NOT NULL,
  num_medicos INT NOT NULL,
  PRIMARY KEY (nombre)
);

-- Tabla servicio
CREATE TABLE IF NOT EXISTS servicio (
  id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_centro_salud INT NOT NULL,
  nombre_tipo_servicio VARCHAR(30) NOT NULL,
  matricula_encargado VARCHAR(30),
  FOREIGN KEY (id_centro_salud) REFERENCES centro_de_salud,
  FOREIGN KEY (nombre_tipo_servicio) REFERENCES tipo_servicio,
  FOREIGN KEY (matricula_encargado) REFERENCES personal
);

-- Tabla personal
CREATE TABLE IF NOT EXISTS personal (
  matricula VARCHAR(30) NOT NULL UNIQUE,
  nombre VARCHAR(30) NOT NULL,
  apellido VARCHAR(30) NOT NULL,
  telefono VARCHAR(30) NOT NULL UNIQUE,
  email VARCHAR(30) NOT NULL UNIQUE,
  nacimiento datetime NOT NULL,
  rol tipo_rol NOT NULL,
  PRIMARY KEY (matricula)
);

-- Tabla personal_servicio
CREATE TABLE IF NOT EXISTS personal_servicio (
  id_servicio INT NOT NULL,
  matricula_personal VARCHAR(30) NOT NULL UNIQUE,
  PRIMARY KEY (id_servicio, matricula_personal),
  FOREIGN KEY (id_servicio) REFERENCES servicio,
  FOREIGN KEY (matricula_personal) REFERENCES personal
);