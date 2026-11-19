"""Reparador automático: bucle validar -> reparar.

Solo agrega filas o reasigna desde pools; nunca borra ni modifica lo
existente. Prefiere arreglos que no cambian conteos antes de los que
agregan filas. Tope de iteraciones; si se agota, aborta con el detalle
de lo no resuelto.

TODO (issue #16): implementar reparar() y el reporte final por tabla.
"""
