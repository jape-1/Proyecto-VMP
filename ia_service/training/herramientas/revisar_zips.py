"""Revisa zips YOLO exportados de Roboflow sin extraerlos."""
import sys, zipfile, collections, posixpath

IMG = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

for ruta in sys.argv[1:]:
    print("=" * 70)
    print(ruta)
    with zipfile.ZipFile(ruta) as z:
        infos = z.infolist()
        yamls = [i.filename for i in infos if i.filename.endswith("data.yaml")]
        for y in yamls:
            print(f"--- {y}")
            print(z.read(y).decode("utf-8", "replace").strip())
        imgs, labs = {}, {}
        tam_img = collections.Counter()
        for i in infos:
            if i.is_dir():
                continue
            d, f = posixpath.split(i.filename)
            stem, ext = posixpath.splitext(f)
            partes = d.split("/")
            split = next((p for p in partes if p in ("train", "valid", "test")), "?")
            if ext.lower() in IMG:
                imgs[(split, stem)] = i
                tam_img[split] += i.file_size
            elif ext == ".txt" and "labels" in partes:
                labs[(split, stem)] = i
        for split in ("train", "valid", "test", "?"):
            ims = [k for k in imgs if k[0] == split]
            lbs = [k for k in labs if k[0] == split]
            if not ims and not lbs:
                continue
            sin_lab = [k for k in ims if k not in labs]
            ids = collections.Counter()
            vacias = malas = poligonos = 0
            for k in lbs:
                txt = z.read(labs[k]).decode("utf-8", "replace").split("\n")
                lineas = [l.split() for l in txt if l.strip()]
                if not lineas:
                    vacias += 1
                for p in lineas:
                    if len(p) < 5:
                        malas += 1
                        continue
                    if len(p) > 5:
                        poligonos += 1
                    ids[p[0]] += 1
            mb = tam_img[split] / len(ims) / 1024 if ims else 0
            print(f"[{split}] imagenes={len(ims)} etiquetas={len(lbs)} "
                  f"img_sin_etiqueta={len(sin_lab)} etiquetas_vacias={vacias} "
                  f"lineas_malas={malas} poligonos={poligonos} "
                  f"objetos_por_id={dict(ids)} KB_prom_img={mb:.0f}")
