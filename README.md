# Inventariado App

Proyecto base en Python con arquitectura estilo IIC2233:
- `cliente/` dividido en `frontend/` y `backend/`.
- `servidor/` con servicios puros.
- `shared/` para DTOs y errores comunes.

## Requisitos

- Python 3.x
- PyQt6

## Instalacion

```bash
pip install -r requirements.txt
```

## Ejecucion

```bash
python main.py
```

## Tests

```bash
python -m unittest
```

## Smoke test de importacion

1. Inicia la app:
   - `python main.py`
2. En la UI de importacion agrega al menos 1 producto valido y presiona `Guardar`.
3. Verifica en `data/output/`:
   - existe un archivo final `import_productos_*.csv`
   - no existe su par `*.inprogress.csv` correspondiente
4. Si ocurre un error al guardar:
   - debe mostrarse un mensaje claro de error
   - puede quedar el `*.inprogress.csv` para reintento o diagnostico

## Supuestos

- El archivo de plantilla de importacion minimo usa columnas:
  - `sku`
  - `nombre`
  - `cantidad`
- En `data/utilities/info_products/*.csv` se elimina solo la columna cuyo header sea
  exactamente `ID` (case-insensitive: `ID`, `Id`, `id`).
- No se elimina `ID Externo` ni `Base EAN13`.
- El nombre por defecto del template es `import_template.csv`.
- La salida por defecto es `data/output/`.

## Migracion info_products

Comandos disponibles:

```bash
python scripts/migrate_info_products.py --dry-run
python scripts/migrate_info_products.py --migrate
python scripts/migrate_info_products.py --migrate --delete-source
```

Reglas de columnas:

- Toda columna faltante en source se completa con `""`.
- Excepcion: `Rastrear Inventario` se completa con `"1"` cuando la columna
  falta o cuando viene vacia/`None`.
- Se aplica alias de header: `Subcaregoría` -> `Subcategoría`.

Seguridad y verificacion:

- Antes de `--migrate` se crea backup de CSV existentes en
  `data/utilities/info_products/_backup_YYYYmmdd_HHMMSS/`.
- Cada archivo migrado se verifica linea por linea contra su source.
- Si hay diferencias, se genera un reporte en
  `data/utilities/info_products/_migration_reports/<categoria>_mismatches.csv`.

Nota de inicializacion:

- Al iniciar la app (`IdRegistry.ensure_initialized`) se normalizan los CSV activos
  en `data/utilities/info_products/*.csv` (solo nivel superior, sin tocar subcarpetas
  de backups/reportes).
- Esta normalizacion reescribe en forma atomica y deja trazas por `logging`.

## Limpieza conservadora

- Se elimino `AppController.register_used_id` porque no tiene referencias en el flujo
  actual de app/tests (`rg register_used_id` sin usos fuera de su definicion).
- `create_import_template` en `cliente/backend/gateway.py` se mantiene aislado como
  API legacy de compatibilidad, con trazas `DEBUG`. No participa del flujo principal
  de importacion (`start/append/finalize`).
- `cliente/frontend/ui/main_window.ui` se mantiene como asset de diseno; la app actual
  construye la UI desde `cliente/frontend/main_window.py` y no carga ese `.ui`
  en runtime.
