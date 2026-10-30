# Vistas

## vw_servicios_abiertos

Lista con los servicios abiertos en el momento de la consulta, mostrando a qué centro pertenece, su dirección y horario de cierre.

### Ejemplo:

| ID_servicio | servicio  | centro                | cierre | depto   | ciudad                 | barrio     | altura |
| ----------- | --------- | --------------------- | ------ | ------- | ---------------------- | ---------- | ------ |
| 12          | Pediatría | Centro de Salud Norte | 20:00  | Uruguay | Concepción del Uruguay | San Martín | 1450   |

---

## vw_historial_internacion

Seguimiento de todas las internaciones históricas y actuales, ordenadas por fecha de ingreso.

### Ejemplo:

| ID_internacion | DNI      | fecha_ingreso | fecha_egreso | tiempo_estadia | responsable      | centro                |
| -------------- | -------- | ------------- | ------------ | -------------- | ---------------- | --------------------- |
| 305            | 30123456 | 2026-10-20    | 2026-10-25   | 5 días         | Dra. Laura Pérez | Centro de Salud Norte |

---

## vw_medico_mas_pacientes

Muestra el médico de cada centro de salud que más pacientes tuvo y la cantidad correspondiente, organizados por barrio. Utiliza la función con la misma descripción.

### Ejemplo:

| ID_centro | centro                | medico         | cant_pacientes | barrio     |
| --------- | --------------------- | -------------- | -------------- | ---------- |
| 3         | Centro de Salud Norte | Dr. Juan Gómez | 148            | San Martín |

---

## vw_top10_pacientes_ingresos

Muestra los 10 pacientes con mayor cantidad de ingresos en centros de salud en el último mes. Utiliza la función con la misma descripción.

### Ejemplo:

| DNI      | paciente        | cant_ingresos | centro_mas_visitado   |
| -------- | --------------- | ------------- | --------------------- |
| 28456789 | María Fernández | 6             | Centro de Salud Norte |

---

## vw_historia_clinica_consolidada

Muestra cada paciente con su historia clínica, mostrando cantidad de internaciones, cantidad de visitas, centro de salud más frecuentado, servicio más usado, obra social (si tiene).

### Ejemplo:

| DNI      | cant_internaciones | cant_visitas | centro_mas_visitado   | servicio_mas_usado | obra_social |
| -------- | ------------------ | ------------ | --------------------- | ------------------ | ----------- |
| 30123456 | 2                  | 14           | Centro de Salud Norte | Clínica Médica     | OSDE        |
