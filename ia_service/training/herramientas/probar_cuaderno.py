import json, zipfile, random, posixpath, collections, shutil, sys, os, ast
from pathlib import Path
nb = json.load(open(sys.argv[1], encoding="utf-8"))
codigo = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
# 1) todas las celdas compilan (quitando magias %)
for i, src in enumerate(codigo):
    ast.parse("\n".join(l for l in src.splitlines() if not l.lstrip().startswith("%")))
print("✅ compilan", len(codigo), "celdas de código")
# 2) mini zips con grupos completos (todas las variantes de cada original elegido)
base = Path("prueba"); shutil.rmtree(base, ignore_errors=True); (base/"zips").mkdir(parents=True)
for nombre, z in {"bicicleta":"externo-bicicleta.zip","moto":"externo-moto.zip","scooter":"externo-scooter-3000.zip"}.items():
    src = zipfile.ZipFile(Path(sys.argv[2], z)); n = src.namelist()
    imgs = [x for x in n if "/images/" in x and not x.endswith("/")]
    g = collections.defaultdict(list)
    for x in imgs: g[posixpath.splitext(posixpath.basename(x))[0].split(".rf.")[0]].append(x)
    elegidos = random.Random(1).sample(sorted(g), 25)
    with zipfile.ZipFile(base/"zips"/z, "w") as o:
        o.writestr("data.yaml", src.read([x for x in n if x.endswith("data.yaml")][0]))
        for k in elegidos:
            for x in g[k]:
                o.writestr(x, src.read(x)); lab = posixpath.splitext(x.replace("/images/","/labels/"))[0]+".txt"
                if lab in n: o.writestr(lab, src.read(lab))
# 3) ejecutar config + funciones + celda de partición con rutas locales
ns = {}
loc = str((base/"content").resolve()).replace("\\","/")
exec(codigo[0], ns)
ns["CARPETA_ZIPS"] = str((base/"zips").resolve()); ns["SALIDAS"] = str((base/"salidas").resolve())
os.makedirs(Path(ns["SALIDAS"],"resultados"), exist_ok=True)
fun = [c for c in codigo if "def particionar" in c][0]
run = [c for c in codigo if "particionar(carpetas" in c][0].replace("/content/", loc + "/")
exec(fun, ns); exec(run, ns)
# 4) verificaciones
ds = base/"content"/"dataset"
donde = collections.defaultdict(set); ids = collections.Counter()
for s in ("train","val","test"):
    for f in (ds/"labels"/s).glob("*.txt"):
        paquete, stem = f.stem.split("__")[0], f.stem.split("__")[1]
        donde[(paquete, stem.split(".rf.")[0])].add(s)
        for l in f.read_text().splitlines(): ids[(paquete, l.split()[0])] += 1
    assert len(list((ds/"images"/s).iterdir())) == len(list((ds/"labels"/s).iterdir()))
fuga = [k for k, v in donde.items() if len(v) > 1]
print("grupos en >1 subconjunto:", len(fuga))
print("ids por paquete:", dict(ids))
assert not fuga
assert {p: i for (p, i) in ids} == {"scooter":"0","bicicleta":"1","moto":"2"}
print((ds/"data.yaml").read_text())
print("✅ partición OK")
