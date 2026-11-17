# Fotos para la prueba lenta (`pytest -m lenta`)

Deja aquí **una** foto real de un scooter o una bicicleta con el nombre
`scooter.jpg`, `bicicleta.jpg`, `scooter.png` o `bicicleta.png`.

La usa `tests/test_ia_real.py` contra el servicio de IA real
(`IA_MODO=http`, `IA_URL=…`). Si no hay foto o no hay servicio, la prueba se
**omite** en lugar de fallar.

Estas imágenes **no se versionan** (`.gitignore`), igual que los pesos del
modelo.
