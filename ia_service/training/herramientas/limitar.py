"""Deja 1 imagen por foto original (sufijo .rf. de Roboflow) y como maximo N originales.
Descarta imagenes sin objetos. Semilla fija. Uso: limitar.py entrada.zip salida.zip N"""
import sys, zipfile, collections, posixpath, random, os
ent, sal, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
if os.path.exists(sal): sys.exit(f"ya existe {sal}, no se sobrescribe")
z = zipfile.ZipFile(ent); n = z.namelist(); labs = set(x for x in n if "/labels/" in x)
g = collections.defaultdict(list)
for x in sorted(n):
    if "/images/" not in x or x.endswith("/"): continue
    lab = posixpath.splitext(x.replace("/images/", "/labels/"))[0] + ".txt"
    if lab in labs and z.read(lab).strip():
        base = posixpath.splitext(posixpath.basename(x))[0].split(".rf.")[0]
        g[base].append((x, lab))
rnd = random.Random(42)
bases = sorted(g); rnd.shuffle(bases); bases = sorted(bases[:N])
cont = collections.Counter(); objs = 0
with zipfile.ZipFile(sal, "w", zipfile.ZIP_STORED) as o:
    for y in [x for x in n if x.endswith("data.yaml") or x.lower().startswith("readme")]:
        o.writestr(y, z.read(y))
    for b in bases:
        img, lab = rnd.choice(g[b])
        o.writestr(img, z.read(img)); t = z.read(lab); o.writestr(lab, t)
        cont[img.split("/")[0]] += 1; objs += len(t.decode().split("\n")) if t.strip() else 0
print("originales disponibles:", len(g), "| elegidas:", len(bases))
print("imagenes por split:", dict(cont), "| objetos:", sum(len(z.read(l).decode().strip().splitlines()) for b in bases for _,l in g[b][:0]) or "ver abajo")
