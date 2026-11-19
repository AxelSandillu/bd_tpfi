"""Emisión del archivo 02_seed.sql.

Genera un solo archivo dentro de BEGIN / COMMIT con INSERT por lotes en el
orden requerido por las FK y los triggers: departamento, ciudad, barrio,
obra_social, paciente, centro_de_salud, personal, especialidad,
especializado_en, tipo_servicio, especialidad_requerida, horario_atencion,
atencion_centro, servicio, atencion_servicio, personal_servicio,
registro_hc, internacion. Los ids van con OVERRIDING SYSTEM VALUE y al
final se hace setval de cada secuencia.

TODO (issue #17): implementar emitir() con escape correcto de comillas,
NULL, booleanos, timestamps, enums y dominio.
"""
