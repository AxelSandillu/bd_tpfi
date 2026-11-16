-- 1. Tabla especialidad
CREATE TABLE especialidad (
    nombre VARCHAR(30) NOT NULL,
    PRIMARY KEY (nombre)
);

-- 2. Tabla especializado_en
CREATE TABLE especializado_en (
    matricula_personal VARCHAR(30) NOT NULL,
    nombre_especialidad VARCHAR(30) NOT NULL,
    PRIMARY KEY (matricula_personal, nombre_especialidad),
    FOREIGN KEY (matricula_personal) REFERENCES personal(matricula),
    FOREIGN KEY (nombre_especialidad) REFERENCES especialidad(nombre)
);

-- 3. Tabla especialidad_requerida
CREATE TABLE especialidad_requerida (
    nombre_tipo_servicio VARCHAR(30) NOT NULL,
    nombre_especialidad VARCHAR(30) NOT NULL,
    PRIMARY KEY (nombre_tipo_servicio, nombre_especialidad),
    FOREIGN KEY (nombre_tipo_servicio) REFERENCES tipo_servicio(nombre),
    FOREIGN KEY (nombre_especialidad) REFERENCES especialidad(nombre)
);

-- 4. Tabla horario_atencion
CREATE TABLE horario_atencion (
    id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    apertura TIME NOT NULL,
    cierre TIME NOT NULL,
    dia DIA NOT NULL
);

-- 5. Tabla atencion_centro
CREATE TABLE atencion_centro (
    id_centro_salud INT NOT NULL,
    id_horario INT NOT NULL,
    PRIMARY KEY (id_centro_salud, id_horario),
    FOREIGN KEY (id_centro_salud) REFERENCES centro_de_salud(id),
    FOREIGN KEY (id_horario) REFERENCES horario_atencion(id)
);

-- 6. Tabla atencion_servicio
CREATE TABLE atencion_servicio (
    id_servicio INT NOT NULL,
    id_horario INT NOT NULL,
    PRIMARY KEY (id_servicio, id_horario),
    FOREIGN KEY (id_servicio) REFERENCES servicio(id),
    FOREIGN KEY (id_horario) REFERENCES horario_atencion(id)
);