# 10 · Seguridad y privacidad

> **[DOC]**: `token_hash` en lugar del token; `contrasena_hash`; el QR guarda un token y no datos personales; consentimiento obligatorio para datos e imágenes (HU01 p.4); vista de espacios solo para seguridad/administración (RF21); trazabilidad con evidencia (RF17); datos en la nube.
> **[PROPUESTA]**: todo el detalle técnico de abajo.
> **Aviso legal:** el proyecto cita la **Ley 29733 (Protección de Datos Personales, Perú)** y su reglamento. Los requisitos concretos (inscripción de bancos de datos, plazos de conservación, base legal, derechos ARCO, transferencia a la nube/extranjero) **se mencionan de memoria y deben verificarse con la UTP/un asesor legal** antes del piloto con datos reales. El código no afirma obligaciones legales específicas: implementa las salvaguardas técnicas y deja los textos legales como **[PENDIENTE]**.

## 1. Datos que maneja el sistema

| Dato | Dónde | Sensibilidad | Observación |
|---|---|---|---|
| Código UTP, nombres, apellidos, correo institucional, sede, tipo de usuario | `usuario_utp` | Personal | Vienen de la UTP; minimizar copias |
| Estado de matrícula | `usuario_utp` | Personal | Solo `activo/inactivo`, no notas ni cursos |
| Foto de referencia del vehículo | S3 + `vehiculo_vmp.foto_referencia_url` | Personal indirecta (puede revelar placa, rostro, domicilio por fondo) | Guía: foto del vehículo sin personas |
| Foto de ingreso / evidencia de IA | S3 + `evento_deteccion_ia.imagen_capturada_url` | Personal (puede captar rostros) | Retención limitada, acceso restringido |
| Historial de ingresos/salidas | `sesion_estacionamiento` | Personal (hábitos de movilidad) | Auditable; acceso por rol |
| Token QR | Móvil del usuario (claro); BD (`token_hash`) | Secreto | Nunca en logs |
| Contraseña del personal | `contrasena_hash` | Secreto | bcrypt |
| Notificaciones | `notificacion` | Personal | Sin ubicación exacta |

Principios: **minimización** (solo lo necesario), **limitación de finalidad** (solo control de acceso y gestión del estacionamiento de VMP, y los indicadores del piloto), **transparencia** (consentimiento claro), **acceso por rol**, **retención limitada**, **trazabilidad**.

## 2. Autenticación y autorización

### 2.1 Roles
| Rol | Quién | Puede | No puede |
|---|---|---|---|
| `usuario` | Estudiante/docente/administrativo UTP | Gestionar **sus** datos, vehículos, QR; ver **sus** avisos; ver estado general (lleno/no lleno) | Ver mapa/detalle de espacios (BR-21), ver datos de otros |
| `seguridad` | Guardia | Operar el punto de acceso, ver espacios/cámaras, gestionar incidencias | Ver reportes de piloto, gestionar personal |
| `administrador` | Personal administrativo del proyecto | Todo lo de seguridad lectura + historial, reportes, personal, mantenimiento de espacios | — |
| `servicio_ia` | `ia_service` | Publicar eventos, leer referencias firmadas | Cualquier endpoint de usuario |

Se aplica en el **API Gateway** (dependencia de FastAPI `requiere_rol([...])`) **y** se verifica propiedad del recurso en el servicio (p. ej. `vehiculo.id_usuario_utp == usuario_actual`). Cada rol nuevo requiere pruebas de autorización.

### 2.2 Sesión
- JWT firmado (HS256 con secreto fuerte o RS256), expira en minutos (`JWT_EXPIRA_MIN`), refresh para el panel. Almacenar en cookie `HttpOnly; Secure; SameSite=Strict` para el panel **[PROPUESTA]**.
- Contraseñas del personal: **bcrypt** (coste ≥ 12), política mínima de longitud, bloqueo temporal tras N intentos fallidos, cambio obligatorio en el primer ingreso.
- El usuario UTP se autentica **vía el Conector** (en producción, SSO de la UTP); el sistema no almacena contraseñas de usuarios UTP.

## 3. Diseño del QR (punto más delicado)

### 3.1 Lo documentado
Un QR por usuario agrupa al usuario y a todos sus vehículos; contiene un **token**, no datos personales; en la BD solo `token_hash`; vigencia por ciclo académico; estados `activo/revocado/expirado`.

### 3.2 Generación **[PROPUESTA]**
```python
token = secrets.token_urlsafe(32)                      # ≥ 256 bits, aleatorio
token_hash = hashlib.sha256(token.encode()).hexdigest() # 64 chars → CODIGO_QR.token_hash
# el QR codifica: "vmp1:" + token      (prefijo con versión para poder cambiar el formato)
```
- El token en claro **solo** se devuelve una vez al cliente que lo muestra (App UTP). Se guarda el hash.
- Lectura: se calcula SHA-256 del token recibido y se busca por `token_hash` (índice único). Comparación en tiempo constante.
- Un solo QR `activo` por usuario (índice único parcial). Regenerar revoca el anterior.
- Editar vehículos “actualiza el QR” (BR-04): como el QR no contiene los vehículos (solo identifica al usuario), basta con que el servidor refleje la lista actual; **[PENDIENTE #4]** decidir si la edición rota el token o solo actualiza la lista asociada.

### 3.3 Riesgos y mitigaciones
| Riesgo | Mitigación |
|---|---|
| **Captura de pantalla / préstamo del QR** | La IA valida además el **vehículo** (segunda barrera); aviso “personal e intransferible”; opción **QR rotatorio** (token TOTP cada 30–60 s) como mejora; alerta si el mismo QR se usa dos veces en poco tiempo o con sesión ya `en_curso` |
| **Reutilización simultánea** (mismo QR en dos accesos) | `ux_sesion_vehiculo_dentro` + chequeo de sesión abierta del usuario |
| **Fuerza bruta de tokens** | 256 bits + *rate limit* por IP/dispositivo en `/acceso/qr` |
| **Fuga de BD** | Solo hashes; imposible reconstruir un QR válido |
| **Fuga de logs** | Prohibido loguear el token; loguear solo `id_qr` |
| **QR de usuario inactivo** | Verificación de `estado_matricula` en cada lectura (BR-08) |

## 4. Imágenes

- **Almacenamiento:** S3/MinIO, buckets privados; la BD solo guarda la clave/URL. Acceso por **URL firmada de corta duración** (`S3_URL_EXPIRA_SEG`). Cifrado en reposo (SSE-KMS).
- **Subida de fotos de referencia:** validar tipo MIME real (no solo extensión), tamaño máx., dimensiones; re-codificar la imagen (descarta metadatos EXIF — incluyen GPS); nombre aleatorio (UUID); antivirus opcional.
- **Evidencias:** guardar el recorte del vehículo y, si es posible, **no** la escena completa; **difuminar rostros** si aparecen **[PROPUESTA]** (detector de rostros simple + blur) o instalar la cámara con ángulo bajo/centrado en el vehículo.
- **Cámaras de zona:** se procesan en el servidor de IA; **no se guardan videos continuos**; solo se guardan fotogramas de eventos (cambio de estado) y de incidencias.
- **Retención:** definida por política **[PENDIENTE docs/13 #10]**; implementar con S3 Lifecycle y un job que borre referencias de vehículos dados de baja.

## 5. Consentimiento y derechos del titular

- **Consentimiento obligatorio** en el registro (HU01 p.4): texto claro sobre qué se recoge (datos, foto del vehículo, fotos en el acceso), para qué (control de acceso, trazabilidad, indicadores del piloto), cuánto tiempo, quién accede, y cómo ejercer derechos. Guardar `acepta_tratamiento_datos`, `fecha_consentimiento` y **versión del texto** aceptado **[PROPUESTA]**.
- **Uso de imágenes para entrenar el modelo:** consentimiento **separado y opcional**. Sin él, las fotos de usuarios reales no entran al dataset. Para el dataset inicial usar fotos propias/voluntarios con permiso.
- **Derechos (acceso, rectificación, cancelación/eliminación, oposición):** el usuario puede ver sus datos y vehículos, corregirlos y darse de baja; la baja elimina fotos y desactiva el QR. Procedimiento para solicitudes manuales vía UTP **[PENDIENTE]**.
- **Registro de accesos** a datos personales (auditoría): quién (personal) consultó qué sesión/imagen y cuándo **[PROPUESTA]** (tabla `auditoria_acceso` opcional).
- **Notificaciones:** nunca incluyen ubicación exacta del espacio ni foto; solo mensajes generales (BR-21).

## 6. Seguridad de la aplicación (checklist OWASP)

| Tema | Medida |
|---|---|
| Inyección SQL | SQLAlchemy con parámetros; prohibido concatenar SQL |
| XSS | React escapa por defecto; sin `dangerouslySetInnerHTML`; CSP en Nginx |
| CSRF | Cookies `SameSite=Strict` + token anti-CSRF para mutaciones del panel |
| Broken access control | Dependencias de rol + chequeo de propiedad + pruebas negativas por cada endpoint |
| Exposición de datos | Esquemas de respuesta explícitos (Pydantic); nunca devolver hashes; paginación |
| Subida de archivos | Ver §4 |
| SSRF | El backend solo llama al conector/IA configurados; URLs de cámara solo desde configuración, no desde entrada del usuario |
| Rate limiting | Nginx + `slowapi` en `/auth/*` y `/acceso/qr` |
| Dependencias | Dependabot + `pip-audit`/`npm audit` en CI |
| Secretos | Secrets Manager / `.env` fuera de Git; `gitleaks` en CI |
| Registro/monitoreo | Logs sin datos personales; alertas de intentos fallidos repetidos |
| Transporte | TLS 1.2+; HSTS; cookies `Secure` |
| Cabeceras | `X-Content-Type-Options`, `X-Frame-Options`/CSP `frame-ancestors`, `Referrer-Policy` |
| Backups | Cifrados; prueba de restauración |

## 7. Seguridad específica de IA

- **Entradas adversarias:** foto de una foto (pantalla/impresión) del vehículo registrado → mitigación: capturar con **cámara propia del acceso** (no subida por el usuario), verificar encuadre y profundidad básica, y alertar patrones repetidos; reconocer que el riesgo no es cero.
- **Integridad del modelo:** pesos en S3 con versionado y checksum (SHA-256) verificado al arrancar; solo CI/CD con aprobación publica un modelo.
- **Datos de entrenamiento:** sin datos de terceros sin permiso; revisar que no incluyan placas legibles ni rostros innecesarios.
- **Sesgo y equidad:** el sistema compara *vehículos*, no personas; aun así, medir tasa de falsos rechazos por **tipo de VMP, color y condiciones de luz** y corregir diferencias.
- **Fallo seguro:** ante duda, la IA **no aprueba sola**: va a zona gris/humano (docs/06 §7.3). Ante caída de IA: modo manual con auditoría.
- **Auditoría de decisiones:** cada decisión guarda modelo/versión, puntajes y evidencia (RNF-06). Cada **override** humano se registra con quién y por qué.

## 8. Qué NO debe hacer el código

1. No loguear, imprimir ni guardar tokens QR, contraseñas, JWT ni URLs firmadas completas.
2. No incluir fotos reales de personas en tests, fixtures ni commits (usar imágenes sintéticas o de vehículos sin personas).
3. No exponer endpoints de espacios/mapa al rol `usuario`.
4. No “resolver” un test fallido de autorización relajando la regla.
5. No afirmar cumplimiento legal; dejarlo como pendiente con el equipo/UTP.
6. No subir `best.pt`, datasets ni `.env` al repositorio.
