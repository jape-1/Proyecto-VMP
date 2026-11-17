# Atribuciones de datasets externos

> CC BY 4.0 exige dar crédito e indicar si se modificó. Fecha de consulta: 2026-11-16.
> Los zips no están en Git: se guardan fuera del repositorio (carpeta local `vmp-datasets/` y Drive `vmp/datasets/`).

| Zip | Clase final | Fuente original (Universe) | Licencia | Copia en nuestro workspace | Modificaciones |
|---|---|---|---|---|---|
| `externo-scooter-3000.zip` | `scooter` | https://universe.roboflow.com/sec-l21ei/mnstr-datast-new-tst | CC BY 4.0 (indicada por el equipo) | `mnstr-datast-new-tst-dry99` v1 | Reducido a 3000 imágenes: 1 por foto original (se quitaron variantes aumentadas), sin imágenes vacías; semilla 42 (`limitar.py`) |
| `externo-bicicleta.zip` | `bicicleta` | **PENDIENTE: enlace original** | CC BY 4.0 (según `data.yaml`) | `bicycle-3ln52-boflm` v1 | Clase renombrada a `bicicleta` |
| `externo-moto.zip` | `moto_electrica` | **PENDIENTE: enlace original** | CC BY 4.0 (según `data.yaml`) | `motorcycle-ojgds-dsshl` v1 | Clase renombrada a `moto_electrica`. Ojo: las imágenes son motos en general (muchas a gasolina) |
