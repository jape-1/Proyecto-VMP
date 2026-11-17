"""Demo de punta a punta contra un backend ya levantado (docs/18 §10).

Uso:
    python scripts/demo_flujo.py                  # contra http://127.0.0.1:8000
    python scripts/demo_flujo.py --url http://127.0.0.1:8010

Recorre los tres casos que hay que mostrar en la exposición:
1. El vehículo coincide  -> puede ingresar.
2. El vehículo no coincide -> bloqueo y decisión manual del guardia.
3. La IA no responde (se simula con un token) -> decisión manual.

Es un cliente más de la API: no toca la base directamente.
"""

from __future__ import annotations

import argparse
import io
import json
import time

import httpx
from PIL import Image, ImageDraw

API = "/api/v1"


def imagen(etiqueta: str) -> bytes:
    """Imagen de prueba válida (> 200 px). El nombre decide la clase en el stub."""
    img = Image.new("RGB", (480, 360), (60, 80, 110))
    dibujo = ImageDraw.Draw(img)
    dibujo.ellipse((60, 180, 160, 280), outline=(240, 240, 240), width=8)
    dibujo.ellipse((300, 180, 400, 280), outline=(240, 240, 240), width=8)
    dibujo.text((16, 16), etiqueta, fill=(255, 255, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class Cliente:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.http = httpx.Client(base_url=self.base, timeout=30)

    def _url(self, ruta: str) -> str:
        return f"{API}{ruta}"

    def sesion_usuario(self, codigo: str) -> dict[str, str]:
        r = self.http.post(self._url(f"/dev/sesion/usuario/{codigo}"))
        r.raise_for_status()
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def sesion_guardia(self, usuario: str) -> dict[str, str]:
        r = self.http.post(self._url(f"/dev/sesion/guardia/{usuario}"))
        r.raise_for_status()
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def pedir(self, metodo: str, ruta: str, **kwargs) -> httpx.Response:
        return self.http.request(metodo, self._url(ruta), **kwargs)


def paso(numero: str, texto: str) -> None:
    print(f"\n[{numero}] {texto}")


def mostrar(datos: dict, campos: tuple[str, ...]) -> None:
    resumen = {c: datos.get(c) for c in campos}
    print("    " + json.dumps(resumen, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--codigo", default="U90000001", help="usuario que registra el scooter")
    parser.add_argument("--guardia", default="guardia.tarde")
    args = parser.parse_args()

    c = Cliente(args.url)

    paso("1", f"El usuario {args.codigo} inicia sesión (dev) y acepta el consentimiento")
    usuario = c.sesion_usuario(args.codigo)
    r = c.pedir(
        "PUT",
        "/usuarios/me/perfil",
        json={"acepta_tratamiento_datos": True, "version_consentimiento": "2026-11"},
        headers=usuario,
    )
    r.raise_for_status()
    mostrar(r.json(), ("codigo_utp", "acepta_tratamiento_datos", "fecha_consentimiento"))

    paso("2", "Registra un scooter y sube la foto de referencia")
    r = c.pedir(
        "POST",
        "/usuarios/me/vehiculos",
        json={
            "tipo_vmp": "scooter_electrico",
            "marca": "Xiaomi",
            "modelo": "Mi 3",
            "color": "negro",
        },
        headers=usuario,
    )
    if r.status_code == 409:
        print("    Ya tiene 3 vehículos; se usa el primero de la lista.")
        existentes = c.pedir("GET", "/usuarios/me/vehiculos", headers=usuario).json()["items"]
        id_vehiculo = existentes[0]["id_vehiculo"]
    else:
        r.raise_for_status()
        id_vehiculo = r.json()["id_vehiculo"]
    print(f"    id_vehiculo={id_vehiculo}")

    r = c.pedir(
        "POST",
        f"/usuarios/me/vehiculos/{id_vehiculo}/foto",
        files={"archivo": ("scooter.png", imagen("scooter"), "image/png")},
        headers=usuario,
    )
    r.raise_for_status()
    mostrar(r.json(), ("id_vehiculo", "tipo_vmp", "tiene_foto"))

    paso("3", "Ve su QR (la imagen viene en base64; la dibuja el frontend)")
    r = c.pedir("GET", "/usuarios/me/qr", headers=usuario)
    r.raise_for_status()
    qr = r.json()
    print(
        f"    id_qr={qr['id_qr']} estado={qr['estado']} vigente={qr['vigente']} "
        f"png={len(qr['imagen_qr_png_base64'])} caracteres base64"
    )

    paso("4", "El guardia inicia sesión (dev)")
    guardia = c.sesion_guardia(args.guardia)
    token = guardia["Authorization"].removeprefix("Bearer ")

    # El QR normal solo devuelve el PNG; en desarrollo hay un endpoint con el texto.
    r = c.pedir("GET", f"/dev/qr/{args.codigo}")
    r.raise_for_status()
    token_qr = r.json()["token"]
    print(f"    token del QR obtenido con GET /dev/qr/{args.codigo} (solo dev)")

    paso("5", "El guardia lee el QR")
    r = c.pedir("POST", "/acceso/qr", json={"token": token_qr}, headers=guardia)
    if r.status_code != 200:
        print(f"    {r.status_code} {r.text}")
        return 1
    lectura = r.json()
    id_sesion = lectura["id_sesion"]
    mostrar(lectura, ("id_sesion", "siguiente_paso"))
    print(f"    usuario: {lectura['usuario']['nombres']} {lectura['usuario']['apellidos']}")

    paso("6", "Captura la foto del vehículo (la IA corre en segundo plano)")
    r = c.pedir(
        "POST",
        f"/acceso/{id_sesion}/captura",
        files={"archivo": ("scooter.png", imagen("scooter"), "image/png")},
        headers=guardia,
    )
    print(f"    {r.status_code} {json.dumps(r.json(), ensure_ascii=False)}")

    paso("7", "Consulta el resultado (polling hasta que la IA responda)")
    estado = {}
    for _ in range(15):
        r = c.pedir("GET", f"/acceso/{id_sesion}", headers=guardia)
        r.raise_for_status()
        estado = r.json()
        if estado["estado"] != "pendiente":
            break
        time.sleep(1)
    mostrar(
        estado,
        ("estado", "motivo", "id_vehiculo_reconocido", "confianza", "mensaje", "puede_decidir"),
    )

    paso("8", "Stream SSE (si el frontend prefiere no consultar cada segundo)")
    with c.http.stream("GET", c._url(f"/acceso/{id_sesion}/stream?token={token}")) as stream:
        for linea in stream.iter_lines():
            if linea.startswith("data: "):
                print("    " + linea[6:])
                break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
