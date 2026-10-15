# Modelo relacional – Centros de salud

```
VAR BASE RELATION departamento (
        id int NOT NULL UNIQUE,
        nombre VARCHAR(30) NOT NULL UNIQUE,
        PRIMARY KEY(id)
)

VAR BASE RELATION ciudad (
        id int NOT NULL UNIQUE,
        id_departamento int NOT NULL,
        nombre VARCHAR(30) NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY(id_departamento) REFERENCES departamento
)

VAR BASE RELATION barrio (
        id int NOT NULL UNIQUE,
        id_ciudad int NOT NULL,
        nombre VARCHAR(30) NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY(id_ciudad) REFERENCES ciudad
)

VAR BASE RELATION obra_social (
        id int NOT NULL UNIQUE,
        razon_social VARCHAR(50) NOT NULL,
        estado boolean NOT NULL,
        PRIMARY KEY(id)
)

VAR BASE RELATION paciente (
        dni int NOT NULL UNIQUE,
        id_obra_social int,
        nombre VARCHAR(30) NOT NULL ,
        apellido VARCHAR(30) NOT NULL,
        nacimiento datetime NOT NULL,
        num_asociado int UNIQUE,
        PRIMARY KEY(dni),
        FOREIGN KEY(id_obra_social) REFENCES obra_social
)

VAR BASE RELATION centro_de_salud (
        id int NOT NULL UNIQUE,
        id_barrio int NOT NULL,
        nombre VARCHAR(30) NOT NULL,
        direccion VARCHAR(50) NOT NULL,
        inaguracion datetime NOT NULL,
        calle VARCHAR(30) NOT NULL,
        altura int NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY(id_barrio) REFERENCES barrio
)

VAR BASE RELATION internacion (
        id int NOT NULL UNIQUE,
        id_registro_hc int NOT NULL,
        fecha_ingreso datetime NOT NULL,
        fecha_egreso datetime,
        PRIMARY KEY(id),
        FOREIGN KEY(id_registro_hc) REFERENCES registro_hc
)

VAR BASE RELATION registro_hc (
        id int NOT NULL UNIQUE,
        id_servicio int NOT NULL,
        dni_paciente int NOT NULL,
        matricula_personal VARCHAR(30) NOT NULL,
        dia_visita datetime NOT NULL,
        diagnostico text NOT NULL,
        tratamiento text NOT NULL,
        PRIMARY KEY(id),
        FOREIGN KEY(id_servicio) REFERENCES servicio,
        FOREIGN KEY(dni_paciente) REFERENCES paciente,
        FOREIGN KEY(matricula_personal) REFERENCES personal
)

VAR BASE RELATION tipo_servicio (
        nombre VARCHAR(30) NOT NULL,
        num_enfermeros int NOT NULL,
        num_medicos int NOT NULL,
        PRIMARY KEY(nombre)
)

VAR BASE RELATION servicio (
        id int NOT NULL UNIQUE,
        id_centro_salud int NOT NULL,
        nombre_tipo_servicio VARCHAR(30) NOT NULL,
        matricula_encargado VARCHAR(30),
        PRIMARY KEY(id),
        FOREIGN KEY(id_centro_salud) REFERENCES centro_de_salud,
        FOREIGN KEY(nombre_tipo_servicio) REFERENCES tipo_servicio,
        FOREIGN KEY(matricula_encargado) REFERENCES personal
)

VAR BASE RELATION personal (
        matricula VARCHAR(30) NOT NULL UNIQUE,
        nombre VARCHAR(30) NOT NULL,
        apellido VARCHAR(30) NOT NULL,
        telefono VARCHAR(30) NOT NULL UNIQUE,
        email VARCHAR(30) NOT NULL UNIQUE,
        nacimiento datetime NOT NULL,
        rol tipo_rol NOT NULL,
        PRIMARY KEY(matricula)
)

VAR BASE RELATION personal_servicio (
        id_servicio int NOT NULL,
        matricula_personal VARCHAR(30) NOT NULL UNIQUE,
        PRIMARY KEY(id_servicio, matricula_personal),
        FOREIGN KEY(id_servicio) REFERENCES servicio,
        FOREIGN KEY(matricula_personal) REFERENCES personal
)

VAR BASE RELATION especialidad (
        nombre VARCHAR(30) NOT NULL UNIQUE,
        PRIMARY KEY(nombre)
)

VAR BASE RELATION especializado_en (
        matricula_personal VARCHAR(30) NOT NULL UNIQUE,
        nombre_especialidad VARCHAR(30) NOT NULL,
        PRIMARY KEY(matricula_personal, id_especialidad),
        FOREIGN KEY(matricula_personal) REFERENCES personal,
        FOREIGN KEY(nombre_especialidad) REFERENCES especialidad
)

VAR BASE RELATION especialidad_requerida (
        nombre_tipo_servicio VARCHAR(30) NOT NULL,
        nombre_especialidad VARCHAR(30) NOT NULL,
        PRIMARY KEY(nombre_tipo_servicio, nombre_tipo_servicio),
        FOREIGN KEY(nombre_tipo_servicio) REFERENCES tipo_servicio,
        FOREIGN KEY(nombre_especialidad) REFERENCES especialidad
)

VAR BASE RELATION horario_atencion (
        id int NOT NULL UNIQUE,
        apertura time NOT NULL,
        cierre time NOT NULL,
        dia Dia NOT NULL,
        PRIMARY KEY(id)
)

VAR BASE RELATION atencion_centro (
        id_centro_salud int NOT NULL UNIQUE,
        id_horario int NOT NULL,
        PRIMARY KEY(id_centro_salud, id_horario),
        FOREIGN KEY(id_centro_salud) REFERENCES centro_de_salud,
        FOREIGN KEY(id_horario) REFERENCES horario_atencion
)

VAR BASE RELATION atencion_servicio (
        id_servicio int NOT NULL UNIQUE,
        id_horario int NOT NULL,
        PRIMARY KEY(id_servicio, id_horario),
        FOREIGN KEY(id_servicio) REFERENCES servicio,
        FOREIGN KEY(id_horario) REFERENCES horario_atencion
)

Dia Enum ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
Rol Enum ("Médico", "Enfermero")
```
