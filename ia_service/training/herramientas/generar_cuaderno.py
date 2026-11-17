"""Genera entrenar_vmp.ipynb (cuaderno de Colab autocontenido). Uso: generar_cuaderno.py salida.ipynb"""
import json, sys

celdas = []
def md(t): celdas.append(("markdown", t.strip("\n")))
def code(t): celdas.append(("code", t.strip("\n")))

md(r"""
# Entrenamiento del detector VMP · 3 clases (YOLO26)

Proyecto: *Servicio de estacionamiento implementado con IA para VMP – UTP Torre Arequipa*.

Este cuaderno hace, en orden: **comprobar GPU → montar Drive → instalar Ultralytics → descomprimir los datasets → unificar clases y repartir train/val/test sin fuga → entrenar → evaluar en test (una sola vez) → guardar todo en Drive**.

**Antes de empezar**
1. *Entorno de ejecución → Cambiar tipo de entorno de ejecución → GPU* (el nombre del menú puede variar).
2. En tu Drive deben estar los zips en `MyDrive/vmp/datasets/`.
3. Ejecuta las celdas **de arriba hacia abajo** (o *Entorno de ejecución → Ejecutar todas*).

⚠ **Aún no hay fotos propias de la Torre Arequipa**: val y test salen de los datasets externos. Las métricas **no representan** el desempeño real en el estacionamiento; se presentan así.
""")

md("## 1 · Configuración (lo único que se edita)")
code(r"""
# --- Rutas en Drive ---
DRIVE_BASE = "/content/drive/MyDrive/vmp"        # carpeta del proyecto en tu Drive
CARPETA_ZIPS = f"{DRIVE_BASE}/datasets"
SALIDAS = f"{DRIVE_BASE}/salidas"                   # runs, resultados y modelos (sobrevive a desconexiones)

# --- Datasets: nombre corto -> zip exportado de Roboflow (formato YOLO) ---
PAQUETES = {
    "bicicleta": "externo-bicicleta.zip",
    "moto": "externo-moto.zip",
    "scooter": "externo-scooter-3000.zip",
}

# --- Clases finales, en este orden (id 0, 1, 2). Se emparejan por NOMBRE con cada data.yaml ---
CLASES = ["scooter", "bicicleta", "moto_electrica"]

# --- Partición (por foto original, dentro de cada paquete) ---
PROPORCIONES = {"train": 0.70, "val": 0.20, "test": 0.10}
SEMILLA = 42

# --- Entrenamiento ---
EXPERIMENTO = "E2-3clases"      # cambia el nombre para un experimento nuevo (p. ej. "E3-yolo26s")
PESOS_INICIALES = "yolo26n.pt"  # "yolo26s.pt" para E3
MODO = "nuevo"                  # "nuevo" o "reanudar" (si Colab se cortó a mitad del entrenamiento)
EPOCAS = 100
PACIENCIA = 20                  # parada temprana: épocas sin mejorar
IMGSZ = 640
BATCH = 16                      # si falla por memoria de GPU, bájalo a 8
TIEMPO_HORAS = None             # p. ej. 2.5 para cortar a las 2,5 h (Colab gratis puede desconectarse)
PERMITIR_CPU = False            # no entrenar en CPU sin querer
""")

md("## 2 · Comprobar la GPU")
code(r"""
import torch, platform
if torch.cuda.is_available():
    print("✅ GPU:", torch.cuda.get_device_name(0))
elif PERMITIR_CPU:
    print("⚠ Sin GPU: entrenar en CPU tardará muchísimo.")
else:
    raise SystemExit("❌ No hay GPU. Entorno de ejecución → Cambiar tipo de entorno → GPU, y vuelve a ejecutar desde arriba.")
print("Python", platform.python_version(), "| torch", torch.__version__)
""")

md("## 3 · Montar Google Drive")
code(r"""
from google.colab import drive
drive.mount("/content/drive")
import os
from pathlib import Path
for p in (SALIDAS, f"{SALIDAS}/runs", f"{SALIDAS}/resultados", f"{SALIDAS}/modelos"):
    os.makedirs(p, exist_ok=True)
faltan = [z for z in PAQUETES.values() if not Path(CARPETA_ZIPS, z).exists()]
if faltan:
    raise SystemExit(f"❌ No encuentro en {CARPETA_ZIPS}: {faltan}")
print("✅ Zips encontrados:", list(PAQUETES.values()))
""")

md("## 4 · Instalar Ultralytics")
code(r"""
%pip install -q -U ultralytics
import ultralytics
print("ultralytics", ultralytics.__version__)
""")

md("""
## 5 · Descomprimir y particionar

Reglas:
- Las clases se emparejan **por nombre** (cada proyecto de Roboflow de una sola clase exporta su clase como id 0; aquí se reescribe al id final).
- Las variantes aumentadas de una misma foto (`foto_jpg.rf.<hash>`) forman **un grupo** y van **juntas** al mismo subconjunto: así ninguna foto está a la vez en train y en test.
- El reparto 70/20/10 se hace **dentro de cada paquete**, para que cada clase tenga val y test.
- Se descomprime en el disco temporal de Colab (`/content`), más rápido que Drive. Re-ejecutar borra y rehace todo (no mezcla corridas).
""")
code(r"""
# Funciones de partición (se usan en la celda siguiente)
import collections, json, random, shutil, zipfile
from pathlib import Path
import yaml

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def descomprimir(zip_path, destino):
    destino = Path(destino)
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(destino)
    return destino

def leer_nombres(carpeta):
    yamls = sorted(Path(carpeta).rglob("data.yaml"))
    if not yamls:
        raise SystemExit(f"❌ {Path(carpeta).name}: no trae data.yaml")
    names = yaml.safe_load(yamls[0].read_text(encoding="utf-8"))["names"]
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names)]
    return list(names)

def grupo_de(stem):
    return stem.split(".rf.")[0]

def convertir_linea(partes, mapa, origen):
    if len(partes) < 5:
        raise SystemExit(f"❌ Etiqueta mal formada en {origen}: {' '.join(partes)}")
    cid = int(float(partes[0]))
    if cid not in mapa:
        raise SystemExit(f"❌ Id de clase {cid} sin nombre conocido en {origen}")
    v = [float(x) for x in partes[1:]]
    if len(v) == 4:
        cx, cy, w, h = v
    else:  # polígono -> caja envolvente
        xs, ys = v[0::2], v[1::2]
        x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
        cx, cy, w, h = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
    return f"{mapa[cid]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"

def particionar(paquetes, salida, clases, proporciones, semilla):
    salida = Path(salida)
    if salida.exists():
        shutil.rmtree(salida)
    subs = ("train", "val", "test")
    for s in subs:
        (salida / "images" / s).mkdir(parents=True)
        (salida / "labels" / s).mkdir(parents=True)
    imgs = collections.Counter(); grupos_n = collections.Counter(); vacias = collections.Counter()
    objs = {s: collections.Counter() for s in subs}
    avisos = []
    for nombre, carpeta in paquetes.items():
        carpeta = Path(carpeta)
        nombres = leer_nombres(carpeta)
        desconocidas = [n for n in nombres if n not in clases]
        if desconocidas:
            raise SystemExit(f"❌ {nombre}: clases {desconocidas} no están en {clases}. Renómbralas en Roboflow.")
        mapa = {i: clases.index(n) for i, n in enumerate(nombres)}
        grupos = collections.defaultdict(list); sin_etiqueta = []
        for img in sorted(carpeta.rglob("*")):
            if img.suffix.lower() not in IMG_EXT or img.parent.name != "images":
                continue
            lab = img.parent.parent / "labels" / (img.stem + ".txt")
            if not lab.exists():
                sin_etiqueta.append(img.name); continue
            grupos[grupo_de(img.stem)].append((img, lab))
        if sin_etiqueta:
            avisos.append(f"{nombre}: {len(sin_etiqueta)} imágenes sin etiqueta omitidas (ej. {sin_etiqueta[:3]})")
        if not grupos:
            raise SystemExit(f"❌ {nombre}: no se encontraron imágenes con etiqueta")
        claves = sorted(grupos)
        random.Random(f"{semilla}-{nombre}").shuffle(claves)
        n = len(claves)
        n_test = max(1, round(n * proporciones["test"]))
        n_val = max(1, round(n * proporciones["val"]))
        asign = {}
        for i, k in enumerate(claves):
            asign[k] = "test" if i < n_test else "val" if i < n_test + n_val else "train"
        for k in claves:
            s = asign[k]; grupos_n[s] += 1
            for img, lab in grupos[k]:
                destino = f"{nombre}__{img.stem}"
                j = 1
                while (salida / "images" / s / (destino + img.suffix.lower())).exists():
                    destino = f"{nombre}__{img.stem}__{j}"; j += 1
                shutil.copy2(img, salida / "images" / s / (destino + img.suffix.lower()))
                lineas = [convertir_linea(l.split(), mapa, lab.name)
                          for l in lab.read_text(encoding="utf-8").splitlines() if l.strip()]
                (salida / "labels" / s / (destino + ".txt")).write_text("\n".join(lineas) + ("\n" if lineas else ""), encoding="utf-8")
                imgs[s] += 1
                if not lineas: vacias[s] += 1
                for l in lineas:
                    objs[s][clases[int(l.split()[0])]] += 1
    data = {"path": str(salida.resolve()), "train": "images/train", "val": "images/val",
            "test": "images/test", "names": {i: c for i, c in enumerate(clases)}}
    (salida / "data.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    for s in ("val", "test"):
        for c in clases:
            if objs[s][c] == 0:
                avisos.append(f"La clase '{c}' no tiene objetos en {s}: sus métricas no se podrán medir.")
    resumen = {"semilla": semilla, "proporciones": proporciones, "clases": clases,
               "imagenes": dict(imgs), "grupos": dict(grupos_n), "imagenes_sin_objetos": dict(vacias),
               "objetos_por_clase": {s: dict(objs[s]) for s in subs}, "avisos": avisos,
               "nota": "val/test salen de datasets EXTERNOS (sin fotos propias): métricas no representativas de la Torre Arequipa"}
    return resumen
""")

code(r"""
import json, time
t0 = time.time()
carpetas = {n: descomprimir(Path(CARPETA_ZIPS, z), f"/content/bruto/{n}") for n, z in PAQUETES.items()}
resumen = particionar(carpetas, "/content/dataset", CLASES, PROPORCIONES, SEMILLA)
DATA_YAML = "/content/dataset/data.yaml"
print(f"Partición en {time.time() - t0:.0f} s\n")
print(f"{'':8}{'imágenes':>10}{'grupos':>8}" + "".join(f"{c:>16}" for c in CLASES))
for s in ("train", "val", "test"):
    print(f"{s:8}{resumen['imagenes'].get(s, 0):>10}{resumen['grupos'].get(s, 0):>8}"
          + "".join(f"{resumen['objetos_por_clase'][s].get(c, 0):>16}" for c in CLASES))
for a in resumen["avisos"]:
    print("⚠", a)
print("\n⚠", resumen["nota"])
Path(SALIDAS, "resultados", f"particion_{EXPERIMENTO}.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
""")

md("""
## 6 · Entrenar

- Todo se guarda **directamente en Drive** (`salidas/runs/<EXPERIMENTO>`), así una desconexión no lo pierde.
- **Si Colab se corta:** vuelve a ejecutar las celdas 1–5 con `MODO = "reanudar"` y luego esta celda; continúa desde `last.pt`.
- Tiempo: no está medido todavía; el cuaderno imprime el tiempo real.
""")
code(r"""
import time, json
from pathlib import Path
from ultralytics import YOLO

RUNS = f"{SALIDAS}/runs"
run_dir = Path(RUNS, EXPERIMENTO)
last = run_dir / "weights" / "last.pt"

t0 = time.time()
if MODO == "reanudar":
    if not last.exists():
        raise SystemExit(f"❌ No hay {last} para reanudar. Usa MODO = 'nuevo'.")
    YOLO(str(last)).train(resume=True)
elif MODO == "nuevo":
    if run_dir.exists():
        raise SystemExit(f"❌ Ya existe {run_dir}. Cambia EXPERIMENTO o usa MODO = 'reanudar'.")
    args = dict(data=DATA_YAML, epochs=EPOCAS, imgsz=IMGSZ, batch=BATCH, patience=PACIENCIA,
                seed=SEMILLA, deterministic=True, project=RUNS, name=EXPERIMENTO, exist_ok=False, plots=True)
    if TIEMPO_HORAS:
        args["time"] = TIEMPO_HORAS
    YOLO(PESOS_INICIALES).train(**args)
else:
    raise SystemExit("❌ MODO debe ser 'nuevo' o 'reanudar'")
segundos = time.time() - t0
BEST = run_dir / "weights" / "best.pt"
print(f"\n✅ Entrenamiento terminado en {segundos/60:.1f} min · mejor modelo: {BEST}")
""")

md("## 7 · Métricas de validación (no toca el test)")
code(r"""
import ultralytics, torch, platform
from datetime import datetime, timezone

def metricas(m, nombres):
    b = m.box
    por_clase = {}
    for i, c in enumerate(b.ap_class_index):
        por_clase[nombres[int(c)]] = {"P": float(b.p[i]), "R": float(b.r[i]),
                                      "mAP50": float(b.ap50[i]), "mAP50_95": float(b.ap[i])}
    return {"P": float(b.mp), "R": float(b.mr), "mAP50": float(b.map50), "mAP50_95": float(b.map),
            "por_clase": por_clase, "ms_por_imagen": {k: round(float(v), 2) for k, v in m.speed.items()},
            "graficos": str(m.save_dir)}

mv = YOLO(str(BEST)).val(data=DATA_YAML, split="val", imgsz=IMGSZ, batch=BATCH,
                          project=RUNS, name=f"{EXPERIMENTO}_val", exist_ok=True)
info_entrenamiento = {
    "experimento": EXPERIMENTO, "pesos_iniciales": PESOS_INICIALES, "modo": MODO,
    "hiperparametros": {"epocas": EPOCAS, "paciencia": PACIENCIA, "imgsz": IMGSZ, "batch": BATCH,
                        "semilla": SEMILLA, "tiempo_horas": TIEMPO_HORAS},
    "segundos_esta_sesion": round(segundos), "imagenes": resumen["imagenes"],
    "entorno": {"python": platform.python_version(), "ultralytics": ultralytics.__version__,
                "torch": torch.__version__, "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"},
    "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "metricas_val": metricas(mv, CLASES),
}
Path(SALIDAS, "resultados", f"{EXPERIMENTO}_entrenamiento.json").write_text(json.dumps(info_entrenamiento, indent=2, ensure_ascii=False))
print(json.dumps(info_entrenamiento["metricas_val"], indent=2, ensure_ascii=False))
""")

md("""
## 8 · Evaluar en TEST (una sola vez por experimento)

El test se usa **una vez**: si el reporte ya existe, la celda se detiene (para no «ajustar» el modelo mirando el test). Genera `salidas/resultados/<EXPERIMENTO>.md` y `.json`.
""")
code(r"""
reporte_md = Path(SALIDAS, "resultados", f"{EXPERIMENTO}.md")
if reporte_md.exists():
    raise SystemExit(f"❌ Ya existe {reporte_md}: el test de este experimento ya se evaluó.")

mt = YOLO(str(BEST)).val(data=DATA_YAML, split="test", imgsz=IMGSZ, batch=BATCH,
                          project=RUNS, name=f"{EXPERIMENTO}_test", exist_ok=False)
r = metricas(mt, CLASES)
ot = resumen["objetos_por_clase"]["test"]
n_test = resumen["imagenes"]["test"]
L = [f"# {EXPERIMENTO} · Evaluación sobre TEST", "",
     "> Generado por el cuaderno `entrenar_vmp.ipynb` (no editar a mano).", "",
     "> ⚠ **El test sale de datasets EXTERNOS** (aún no hay fotos propias). Estas cifras **no representan** el desempeño en la Torre Arequipa.", "",
     "| Dato | Valor |", "|---|---|",
     f"| Fecha | {datetime.now(timezone.utc).isoformat(timespec='seconds')} |",
     f"| Pesos | `{BEST}` (inicio: `{PESOS_INICIALES}`) |",
     f"| imgsz | {IMGSZ} |",
     f"| Imágenes de test | **{n_test}** |",
     f"| Objetos de test por clase | " + ", ".join(f"{c}: {ot.get(c, 0)}" for c in CLASES) + " |",
     f"| Entorno | python {info_entrenamiento['entorno']['python']}, ultralytics {info_entrenamiento['entorno']['ultralytics']}, "
     f"torch {info_entrenamiento['entorno']['torch']}, gpu {info_entrenamiento['entorno']['gpu']} |", "",
     "## Métricas globales (test)", "", "| P | R | mAP50 | mAP50-95 |", "|---|---|---|---|",
     f"| {r['P']:.3f} | {r['R']:.3f} | {r['mAP50']:.3f} | {r['mAP50_95']:.3f} |", "",
     "## Por clase (test)", "", "| Clase | Objetos | P | R | mAP50 | mAP50-95 |", "|---|---|---|---|---|---|"]
for c in CLASES:
    m = r["por_clase"].get(c)
    L.append(f"| {c} | {ot.get(c, 0)} | " + (f"{m['P']:.3f} | {m['R']:.3f} | {m['mAP50']:.3f} | {m['mAP50_95']:.3f} |" if m else "— | — | — | — |"))
s = r["ms_por_imagen"]
L += ["", "## Velocidad (ms por imagen, en la GPU de Colab)", "", "| Preproceso | Inferencia | Posproceso |", "|---|---|---|",
      f"| {s.get('preprocess', 0)} | {s.get('inference', 0)} | {s.get('postprocess', 0)} |", "",
      "**No vale para la laptop del demo** (medir allí aparte).", "",
      "## Gráficos", "", f"Matriz de confusión y curvas en: `{r['graficos']}`"]
if n_test < 100:
    L.insert(4, f"> ⚠ Solo {n_test} imágenes de test: las cifras son inestables.\n")
reporte_md.write_text("\n".join(L) + "\n", encoding="utf-8")
Path(SALIDAS, "resultados", f"{EXPERIMENTO}.json").write_text(
    json.dumps({"test": r, "imagenes_test": n_test, "objetos_test": ot}, indent=2, ensure_ascii=False))
print("\n".join(L))
""")

md("## 9 · Ver la matriz de confusión y ejemplos del test")
code(r"""
from IPython.display import Image as IPImage, display
from PIL import Image
import random
cm = Path(r["graficos"], "confusion_matrix_normalized.png")
if cm.exists():
    display(IPImage(filename=str(cm), width=700))
ejemplos = sorted(Path("/content/dataset/images/test").iterdir())
random.Random(SEMILLA).shuffle(ejemplos)
modelo = YOLO(str(BEST))
for res in modelo.predict([str(p) for p in ejemplos[:6]], conf=0.25, imgsz=IMGSZ, verbose=False):
    display(Image.fromarray(res.plot()[..., ::-1]).resize((480, int(480 * res.orig_shape[0] / res.orig_shape[1]))))
""")

md("## 10 · Guardar el modelo final")
code(r"""
import shutil
destino = Path(SALIDAS, "modelos", f"{EXPERIMENTO}-best.pt")
shutil.copy2(BEST, destino)
print("✅ Modelo:", destino)
print("✅ Reportes:", Path(SALIDAS, "resultados"))
print("Descárgalo desde Drive a tu laptop. NO lo subas a Git.")
""")

nb = {"nbformat": 4, "nbformat_minor": 5,
      "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                   "kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}},
      "cells": []}
for i, (tipo, src) in enumerate(celdas):
    lineas = src.split("\n")
    fuente = [l + "\n" for l in lineas[:-1]] + [lineas[-1]]
    c = {"cell_type": tipo, "id": f"c{i:02d}", "metadata": {}, "source": fuente}
    if tipo == "code":
        c.update({"execution_count": None, "outputs": []})
    nb["cells"].append(c)
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print("ok", sys.argv[1], len(celdas), "celdas")
