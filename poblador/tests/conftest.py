"""Configuración de pytest para el proyecto poblador.

Agrega el directorio padre de tests/ al sys.path para que los módulos
de nivel superior (config, generadores, fuentes, etc.) sean importables.
"""

import sys
from pathlib import Path

# El directorio poblador/ (padre de tests/) debe estar en el path.
POBLADOR_DIR = Path(__file__).resolve().parent.parent
if str(POBLADOR_DIR) not in sys.path:
    sys.path.insert(0, str(POBLADOR_DIR))
