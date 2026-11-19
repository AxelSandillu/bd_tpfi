"""Validador independiente de las tablas generadas en memoria.

Recorre las tablas ya armadas sin usar los pools y devuelve violaciones
(tabla, fila, regla). Verifica UNIQUE, largos máximos, regex (matrícula,
teléfono, email), FK resueltas, cupos y especialidades por servicio, un
servicio por persona, (centro, tipo) único, encargado médico, registros
atendidos por un médico del servicio, ingreso = visita, egreso >= ingreso,
fechas anteriores a hoy, visitas dentro del horario del servicio e
internaciones sin solapamiento.

TODO (issue #15): implementar validar() y todas las reglas de la sección 10.
"""
