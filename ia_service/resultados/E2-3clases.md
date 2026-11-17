# E2-3clases · Evaluación sobre TEST

> Generado por el cuaderno `entrenar_vmp.ipynb` (no editar a mano).

> ⚠ **El test sale de datasets EXTERNOS** (aún no hay fotos propias). Estas cifras **no representan** el desempeño en la Torre Arequipa.

| Dato | Valor |
|---|---|
| Fecha | 2026-11-17T05:56:08+00:00 |
| Pesos | `/content/drive/MyDrive/vmp/salidas/runs/E2-3clases/weights/best.pt` (inicio: `yolo26n.pt`) |
| imgsz | 640 |
| Imágenes de test | **785** |
| Objetos de test por clase | scooter: 408, bicicleta: 200, moto_electrica: 339 |
| Entorno | python 3.13.16, ultralytics 8.4.215, torch 2.14.1+cu130, gpu Tesla T4 |

## Métricas globales (test)

| P | R | mAP50 | mAP50-95 |
|---|---|---|---|
| 0.940 | 0.945 | 0.969 | 0.734 |

## Por clase (test)

| Clase | Objetos | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| scooter | 408 | 0.906 | 0.893 | 0.936 | 0.665 |
| bicicleta | 200 | 0.952 | 0.975 | 0.981 | 0.743 |
| moto_electrica | 339 | 0.962 | 0.968 | 0.990 | 0.794 |

## Velocidad (ms por imagen, en la GPU de Colab)

| Preproceso | Inferencia | Posproceso |
|---|---|---|
| 1.11 | 4.07 | 1.92 |

**No vale para la laptop del demo** (medir allí aparte).

## Gráficos

Matriz de confusión y curvas en: `/content/drive/MyDrive/vmp/salidas/runs/E2-3clases_test`
