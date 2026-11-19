"""Pools de recursos para la generación de datos en memoria.

Contiene los consumibles (cada elemento se usa una vez) y los reutilizables
(se sortea con reposición), indexados por atributo.

TODO (issue #11): implementar tomar(n), sorteo con reposición, agotamiento
y reintento con semilla derivada hasta MAX_REINTENTOS.
"""
