# Entrenamiento (siempre en Colab, nunca en local)

| Archivo | Para qué |
|---|---|
| `entrenar_vmp.ipynb` | Cuaderno de Colab: parte los zips por foto original (70/20/10, semilla 42), entrena YOLO26, evalúa sobre test una sola vez y escribe los reportes de `../resultados/` |
| `herramientas/generar_cuaderno.py` | Genera el cuaderno: `python generar_cuaderno.py entrenar_vmp.ipynb`. El cuaderno no se edita a mano |
| `herramientas/probar_cuaderno.py` | Prueba local de la partición con una muestra: `python probar_cuaderno.py entrenar_vmp.ipynb <carpeta-de-zips>` |
| `herramientas/limitar.py` | Reduce un zip a N fotos originales: `python limitar.py entrada.zip salida.zip 3000` |
| `herramientas/revisar_zips.py` | Cuenta imágenes, objetos y originales de un zip sin extraerlo |

Estas herramientas todavía no tienen pruebas con `pytest`: es una tarea pendiente (`docs/16`).
