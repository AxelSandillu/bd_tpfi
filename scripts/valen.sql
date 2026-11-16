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
      nacimiento DATETIME NOT NULL,
      num_asociado INT UNIQUE,
      FOREIGN KEY (id_obra_social) REFERENCES obra_social
);

-- Tabla: Centro de salud
CREATE TABLE IF NOT EXISTS centro_de_salud (
      id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      id_barrio INT NOT NULL,
      nombre VARCHAR(30) NOT NULL UNIQUE,
      direccion VARCHAR(30) NOT NULL,
      inaguracion DATETIME NOT NULL,
      calle VARCHAR(30) NOT NULL,
      altura INT NOT NULL,
      FOREIGN KEY (id_barrio) REFERENCES barrio
);


