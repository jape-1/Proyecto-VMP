# 17 · Entrenamiento en Google Colab (Fase 1)

> **[PROPUESTA]**. Decisión del equipo (14-nov-2026): **el entrenamiento y la evaluación se hacen en Colab**, no en las laptops, para no gastar los recursos propios. Lo que es propenso a cambiar (límites de uso gratuito, GPU asignada, nombres de menús) está marcado con ⚠: confírmalo en pantalla o en la documentación de Colab.

## 1. Qué corre dónde

| Tarea | Dónde | Por qué |
|---|---|---|
| Armar y anotar el dataset | **Roboflow** (web) | Trabajo en grupo; sin cómputo local |
| Partición del dataset, E1, **entrenar**, **evaluar** | **Colab con GPU** | Es lo pesado; la GPU gratuita lo hace en minutos u horas en vez de horas o días en CPU |
| Pruebas automáticas, escribir código, `git` | Laptop | Liviano |
| **Demo** (inferencia con `best.pt`) | Laptop en CPU, o Colab como plan B | El modelo nano es liviano **para inferencia**; entrenar es lo caro |

El entrenamiento no se ejecuta en la laptop: el código y el cuaderno están en `ia_service/training/` y **una persona del equipo** lo abre y lo corre en Colab.

## 2. Preparación (una vez, la hace Giancarlo)

1. **Google Drive:** crear la carpeta `vmp-fase1/` y compartirla con los otros tres (permiso de edición). Dentro:
   - `datasets/externo-1.zip`, `externo-2.zip`… → una exportación YOLO **por cada proyecto externo** de Roboflow (p. ej. `base-externa`, o el de bicicletas y el de scooters).
   - `datasets/propias.zip` → exportación YOLO del proyecto `vmp-propias`.
   - `salidas/` → aquí se guardan resultados y pesos (§3 paso 8).
2. **El código en Colab:** el cuaderno trae `ia_service/` desde GitHub (si el repositorio es privado: un *token* de solo lectura guardado en los **Secrets** de Colab ⚠, nunca escrito en el cuaderno) o desde un `.zip` en Drive (ver `ia_service/training/LEEME.md`).
3. **Roboflow:** lo más simple es **exportar a mano** y subir los `.zip` a Drive (no hace falta clave de API). Si más adelante se usa la API de Roboflow desde Colab, la clave va en los **Secrets** de Colab, no en el cuaderno ni en Git.

## 3. Paso a paso en Colab

1. Abrir el cuaderno `ia_service/notebooks/…` en Colab (desde GitHub o Drive).
2. **Activar la GPU:** *Entorno de ejecución → Cambiar tipo de entorno de ejecución → acelerador por hardware: GPU* ⚠ (el nombre del menú y la GPU asignada, típicamente una T4, pueden variar y no está garantizada).
3. **Montar Drive** y ubicarse en `vmp-fase1/`.
4. **Instalar dependencias** (Ultralytics y lo que pida `requirements.txt`) y comprobar que ve la GPU (el cuaderno debe mostrar un mensaje claro si no la ve: **detenerse y avisar**, no entrenar en CPU sin querer).
5. **Descomprimir** los `externo-*.zip` y `propias.zip` en el disco temporal de Colab (más rápido que trabajar sobre Drive).
6. **Partición** con `split_dataset` (`docs/16` §3) → `dataset/` con `data.yaml`. Revisar el resumen impreso: imágenes por subconjunto, objetos por clase, subconjuntos vacíos.
7. **E1** (línea base cualitativa, `docs/16` §6.3) y luego **entrenar E2** con `yolo26n.pt`; después **evaluar en test** (`docs/16` §6.2).
8. **Guardar en Drive** (`salidas/`): `best.pt`, `last.pt`, `resultados/*.md|json`, matriz de confusión y curvas. Hacerlo **al terminar y también durante el entrenamiento** (cada corrida debe escribir sus `runs/` directamente en Drive, para que una desconexión no lo pierda).
9. Descargar `best.pt` a la laptop **sin subirlo a Git**.

## 4. Cuidados propios de Colab ⚠

- **Las sesiones se cortan** (por inactividad o por límite de tiempo, y el uso gratuito tiene cupos que cambian). Por eso: guardar en Drive, usar **reanudación** del entrenamiento (`resume`) y, si hace falta, limitar la duración del entrenamiento. No dejar el navegador abierto sin usar: se pierde cupo.
- **Disco temporal:** lo que está en `/content` desaparece al terminar la sesión; solo sobrevive lo que está en Drive.
- **Cada cuenta de Google tiene su propio cupo.** Si el de una persona se agota, otra del equipo puede abrir el mismo cuaderno con su cuenta (la carpeta de Drive es compartida).
- **Tiempos:** con `yolo26n`, `imgsz` 640 y del orden de unos cientos a pocos miles de imágenes, se espera que tarde **desde decenas de minutos hasta pocas horas** en una GPU gratuita. Es una **estimación sin medir**; el cuaderno debe imprimir el tiempo real y se anota en el reporte.
- **Memoria de GPU:** si falla por memoria, bajar `batch` o `imgsz`; no cambiar nada más sin avisar.
- **Reproducibilidad:** misma semilla; anotar en el reporte la versión de Ultralytics y de Python que muestre el cuaderno.

## 5. Demo después del entrenamiento

- **Principal:** en la laptop, con `best.pt` y `demo/detectar.py` (`docs/15`). Inferencia en CPU con el modelo nano: ligera. La webcam solo funciona en local.
- **Plan B (si la laptop falla):** ejecutar el demo en Colab sobre una carpeta de imágenes y mostrar las imágenes anotadas dentro del cuaderno (en Colab no se abren ventanas de OpenCV). Además, siempre llevar el **video de respaldo** (`docs/15` §5).

## 6. Checklist antes de gastar tiempo de GPU

- [ ] `externo-*.zip` y `propias.zip` en Drive, exportados en formato YOLO **sin aumentos** (`docs/14` §6).
- [ ] Nombres de las clases en Roboflow: exactamente `scooter` y `bicicleta`.
- [ ] El cuaderno ya corrió la partición y mostró conteos por clase razonables (ninguna clase casi vacía; val y test con fotos propias).
- [ ] GPU activa y detectada.
- [ ] Carpeta de salida en Drive.
- [ ] Alguien sabe reanudar si se corta.

## 7. Qué NO hacer

- Entrenar en la laptop «por probar»: gasta recursos y batería, y ya hay otro lugar para ello.
- Guardar `best.pt` o datasets en GitHub.
- Poner claves (Roboflow, GitHub) dentro del cuaderno.
- Evaluar en `test` varias veces para «ajustar» el modelo: el test se usa **una vez por experimento** (`docs/16` §6.2).
