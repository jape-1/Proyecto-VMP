# 19 · Requisitos del avance (qué entra en la prueba y cómo se acepta)

> **[PROPUESTA]** salvo lo marcado **[DOC]**. Recorta `docs/02` (RF01–RF22, BR-01…BR-30, RNF) y `docs/03` (24 HU) al alcance de `docs/18`: **flujo del usuario + flujo del guardia, solo ingreso, detector real, base de datos, backend y dos frontends**. Lo que no entra sigue siendo el objetivo del producto completo, pero **no se construye** en este avance. Objetivo inmediato (decisión 16-nov-2026): **probar el sistema el 17-nov-2026.**

Leyenda: ✅ entra · 🟡 entra parcialmente (se dice cuánto) · ⛔ fuera de este avance.

## 1. Requisitos funcionales

| RF | Requisito (resumen) | HU | Alcance | Nota |
|---|---|---|---|---|
| RF01 | Registro del usuario vía Portal UTP | HU01 | 🟡 | Datos traídos del Conector simulado + perfil + consentimiento; **sin pantalla de login** (sesión ya iniciada, `docs/18` §4) |
| RF02 | Hasta 3 VMP por usuario | HU02 | ✅ | |
| RF03 | Foto de referencia por vehículo | HU03 | ✅ | Validada con el detector real |
| RF04 | Editar o eliminar vehículo | HU04 | 🟡 | La regla «no eliminar si está dentro» queda incompleta sin salida (`docs/18` §7.9) |
| RF05 | QR único por usuario | HU05 | ✅ | |
| RF06 | Mostrar el QR en la App | HU06 | ✅ | Frontend del usuario (vista móvil) |
| RF07 | Escanear el QR en el ingreso | HU07, HU08 | ✅ | Frontend del guardia; con respaldo de ingreso manual del token |
| RF08 | Capturar foto del vehículo | HU09 | ✅ | |
| RF09 | Comparar con IA | HU10 | 🟡 | **Detector real que confirma el tipo registrado, no la identidad** (`docs/18` §5). **Desde el 17-nov entra también la semejanza con la foto registrada** (`docs/26`) |
| RF10 | Validar y confirmar correspondencia | HU11 | 🟡 | Idem: «hay un vehículo del tipo registrado» |
| RF11 | Rechazar / incidencia si no coincide | HU12 | 🟡 | Bloqueo + decisión del guardia + registro; **sin gestión de incidencias** |
| RF12–RF15 | Cámaras, ocupación, liberación, tiempo real | HU13–HU16 | ⛔ | Control de espacios fuera |
| RF16 | Panel con ubicación de espacios | HU17 | ⛔ | |
| RF17 | Historial de ingresos, salidas, incidencias | HU18 | 🟡 | **Solo ingresos** (aceptados y rechazados); HU19 (salidas) y HU20 (incidencias) fuera |
| RF18 | Consultar y filtrar historial | HU21 | ⛔ | Opcional: una lista simple de ingresos para el guardia |
| RF19 | Notificar ingreso al usuario | HU22 | ⛔ | El «aviso» del avance es del sistema al **guardia**, no push al usuario |
| RF20 | Aviso de estacionamiento lleno | HU23 | ⛔ | |
| RF21 | El usuario no ve el detalle de espacios | — | ✅ | Se cumple por construcción (no existe esa vista) y por 403 |
| RF22 | Reportes del piloto | HU24 | ⛔ | |

## 2. Reglas de negocio

| Regla | Alcance |
|---|---|
| BR-01 máximo 3 VMP activos | ✅ |
| BR-02 foto con vehículo | ✅ |
| BR-03 no eliminar un vehículo «dentro» | 🟡 (ver nota RF04) |
| BR-04 editar actualiza el QR | ✅ (seguir `docs/13` #4) |
| BR-05 un QR por usuario con solo un token | ✅ |
| BR-06 vigencia y estados del QR | ✅ |
| BR-07 QR vencido/alterado/inexistente rechazado | ✅ |
| BR-08 matrícula vigente | ✅ (del Conector simulado) |
| BR-09 cámara de ingreso solo tras leer el QR | ✅ |
| BR-10 foto guardada con ID del QR y hora | ✅ |
| BR-11 similitud con cada vehículo | 🟡 (regla v1 por tipo, `docs/18` §5; **semejanza por vector desde el 17-nov, `docs/26`**) |
| BR-12 resolverse «en segundos» | ✅ (medir y reportar el tiempo real, no prometer) |
| BR-13 validado → «puede ingresar», guarda el ingreso | 🟡 (sin notificación al usuario) |
| BR-14 no coincide → bloquear, evidencia, decide el humano | 🟡 (sin alerta en tiempo real a un panel de incidencias; sí al guardia) |
| BR-15 intentos fallidos se guardan | ✅ |
| BR-16–BR-20, BR-24–BR-28 | ⛔ |
| BR-21 usuario no ve espacios | ✅ (no existe la vista) |
| BR-22–BR-23 notificaciones | ⛔ |
| BR-29 consultas al Portal/App UTP registradas | ✅ (`sincronizacion_utp`) |
| BR-30 consentimiento obligatorio | ✅ (dónde guardarlo: brecha B3, pedir aprobación antes de crear columnas) |

## 3. Requisitos no funcionales que se vigilan en este avance

| RNF | Qué se exige ahora |
|---|---|
| RNF-01 | Medir y mostrar el tiempo real QR leído → resultado (sin prometer cifra) |
| RNF-03 | Si la IA falla, el guardia decide a mano y queda registrado |
| RNF-04 | Hash de tokens y contraseñas, secretos por variables de entorno, acceso por rol |
| RNF-05 | Consentimiento, imágenes sin acceso público, sin datos personales en logs |
| RNF-06 | Cada decisión guarda evidencia (imagen, confianza, versión del modelo, hora) |
| RNF-07 | El Conector UTP es el único punto de contacto con «sistemas UTP» |
| RNF-09 | Mensajes claros (`docs/08` §7) |
| RNF-11 | Todo corre con `docker compose up` en una laptop |
| RNF-12 | Ninguna cifra de precisión sin medirla (`docs/06`) |

## 4. Criterios de aceptación (escenarios)

**Usuario**
1. *Dado* un usuario con 2 vehículos, *cuando* registra un tercero, *entonces* se crea y el contador marca 3 de 3. *Cuando* intenta un cuarto, *entonces* recibe `LIMITE_VMP_ALCANZADO` y un mensaje claro.
2. *Cuando* sube una foto sin scooter ni bicicleta, *entonces* recibe `FOTO_SIN_VEHICULO` y la foto no se guarda como referencia.
3. *Cuando* no ha aceptado el consentimiento, *entonces* no puede registrar vehículos (`CONSENTIMIENTO_REQUERIDO`).
4. *Dado* un usuario con vehículos con foto, *cuando* abre su QR, *entonces* ve el QR, su vigencia y la lista de vehículos; el QR **no** contiene datos personales.
5. *Cuando* regenera el QR, *entonces* el anterior queda revocado y es rechazado en el acceso.

**Guardia**
6. *Dado* un QR válido, *cuando* el guardia lo lee, *entonces* ve al usuario y sus vehículos con foto y puede capturar la foto del vehículo.
7. *Dado* un QR vencido, alterado, revocado o inexistente, *entonces* se rechaza con el mensaje específico y el intento queda registrado.
8. *Dado* un scooter registrado y una foto de un scooter, *entonces* el resultado es `validado` y se muestra qué vehículo coincidió por tipo.
9. *Dado* un usuario que solo registró bicicletas y una foto de un scooter, *entonces* el resultado es `rechazado` (`VEHICULO_NO_COINCIDE`) y decide el guardia.
10. *Dado* una foto sin vehículo o con confianza dudosa, *entonces* el resultado es `verificar` y decide el guardia.
11. *Dado* el servicio de IA apagado, *entonces* se muestra «IA no disponible: modo manual» y el guardia aprueba o rechaza con motivo; queda registrado.
12. Cada intento (validado, rechazado, verificado a mano, QR inválido) queda en el registro con hora, imagen y decisión.

**Transversal**
13. El usuario recibe 403 al llamar a endpoints del guardia y viceversa.
14. Ninguna respuesta devuelve `token_hash`, contraseñas ni datos de otro usuario.
15. `docker compose up` levanta base de datos, backend, IA y los dos frontends; los datos de ejemplo permiten repetir la demo desde cero.
16. Las pruebas automáticas de las reglas anteriores están en verde y su salida real se muestra.

## 5. Fuera de alcance explícito (no construir)

Control de espacios, cámaras de zona, ocupación/liberación, salida, gestión de incidencias, panel administrativo, historial con filtros y exportación, reportes e indicadores, notificaciones push, aviso de estacionamiento lleno, encuestas, multisede, despliegue en AWS/Terraform, `moto` en el detector.
