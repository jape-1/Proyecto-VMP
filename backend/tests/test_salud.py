def test_cors_acepta_la_red_local_en_desarrollo(cliente):
    """Para abrir la App desde un celular en la misma Wi-Fi (http://192.168.x.x:5173)."""
    for origen, aceptado in [
        ("http://192.168.1.34:5173", True),
        ("http://10.0.0.8:5173", True),
        ("http://localhost:5173", True),
        ("https://sitio-ajeno.com", False),
        ("http://192.168.1.34.ajeno.com", False),
    ]:
        respuesta = cliente.options(
            "/salud",
            headers={"Origin": origen, "Access-Control-Request-Method": "GET"},
        )
        permitido = respuesta.headers.get("access-control-allow-origin") == origen
        assert permitido is aceptado, origen
