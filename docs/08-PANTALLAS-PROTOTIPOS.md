# 08 · Pantallas, prototipos y experiencia por actor

> **[DOC]**: los 24 prototipos de baja fidelidad del Avance 2 (uno por HU) y sus anotaciones numeradas; se reproducen completos en `docs/03-BACKLOG-HU.md` (§6, «Comportamiento del prototipo»). **Este archivo los reorganiza por superficie** (Portal, App, Punto de acceso, Panel) y agrega la especificación de implementación **[PROPUESTA]**: rutas, componentes, estados y mensajes. Las imágenes originales de los prototipos están en el PDF del Avance 2; aquí no se reproducen.

## 1. Superficies

| Superficie | Quién | Dispositivo | ¿Quién la construye? | HU |
|---|---|---|---|---|
| **Portal UTP** (registro y vehículos) | Usuario | Web | Simulada (`simulador_utp/`) | HU01–HU05 |
| **App UTP** (QR y notificaciones) | Usuario | Móvil | Simulada (`simulador_utp/`, vista móvil) | HU06, HU22, HU23 |
| **Punto de acceso** | Guardia + usuario | Tablet + lector + cámara de ingreso | Propia (`panel/` ruta `/acceso`) | HU07–HU12 |
| **Panel de seguridad** | Seguridad | Web | Propia (`panel/`) | HU13–HU17, HU20 |
| **Panel administrativo** | Administración | Web | Propia (`panel/`) | HU17–HU21, HU24 |

> El Portal UTP y la App UTP son sistemas **existentes** de la UTP; el proyecto no los construye ni los modifica. Para el prototipo se simulan lo mínimo necesario para demostrar el flujo (**[PROPUESTA]**).

## 2. Mapa de navegación **[PROPUESTA]**

```
Portal UTP (simulado)                         App UTP (simulada, móvil)
 /login ─▶ /registro (4 pasos) ─▶ /vehiculos     /qr ──── QR + vehículos autorizados + aviso intransferible
            ├─ paso 1 datos (traídos del Portal)  /avisos ─ historial de notificaciones (+ «No reconozco este ingreso»)
            ├─ paso 2 tipo de usuario/contacto    /estado ─ «Hay espacio / Estacionamiento lleno» (+ suscribirse)
            ├─ paso 3 consentimiento
            └─ paso 4 vehículos y fotos

Panel (React)  login ─▶  rol seguridad:  /acceso  /espacios  /camaras  /incidencias  /historial
                         rol administrador: /espacios  /incidencias  /historial  /reportes  /personal
```

## 3. Pantallas del Portal UTP (simulado)

### 3.1 Registro en 4 etapas — HU01
- **Indicador de pasos** visible (1/4 … 4/4).
- Paso 1: datos **precargados** desde el Conector (código, nombres, correo, sede, estado de matrícula), de solo lectura (HU01 p.2).
- Paso 2: el usuario completa **solo** lo que el Portal no tiene: tipo de usuario y contacto (HU01 p.3).
- Paso 3: **consentimiento obligatorio** (uso de datos e imágenes). Sin marcar → no avanza (`CONSENTIMIENTO_REQUERIDO`).
- Paso 4: lleva al registro de vehículos.
- Si el estado de matrícula es `inactivo` → mensaje «Tu matrícula no está vigente; no puedes usar el servicio» y no continúa.

### 3.2 Mis vehículos — HU02, HU03, HU04
- **Contador** «2 de 3 vehículos» (HU02 p.1). Al llegar a 3, el botón «Agregar» se deshabilita y se explica por qué (HU02 p.3); si por API llega un cuarto → 409 con el mensaje de límite.
- **Formulario:** tipo (lista de `tipo_vmp`), marca, modelo, color, característica distintiva (opcional, 255).
- **Una pestaña por vehículo**, con un **check** cuando ya tiene foto (HU03 p.1).
- **Carga de foto:** subir archivo o tomar desde el celular (`<input capture>`) (HU03 p.2); **pautas visibles** para una buena foto (HU03 p.3): vehículo completo, fondo despejado, buena luz, vista lateral, sin filtros.
- **Validación previa:** si la imagen no contiene un vehículo → «No detectamos un vehículo en la foto. Intenta de nuevo» (`FOTO_SIN_VEHICULO`) (HU03 p.4). **[PROPUESTA]** además: tamaño mínimo, formatos `jpg/png/webp`, máx. 5 MB, nitidez mínima.
- **Editar / Eliminar** por vehículo (HU04 p.1). Editar → guarda y **el QR se actualiza** (aviso «Tu QR se actualizó automáticamente»). Eliminar → **confirmación** («¿Eliminar este vehículo?») (HU04 p.3); si el vehículo figura «dentro» → bloqueo con explicación (HU04 p.4).

### 3.3 QR generado — HU05
Muestra: identificador del QR, **vigencia** (ciclo académico) y estado; aclara que **un solo QR agrupa al usuario y hasta 3 vehículos**; aviso de que el código guarda un token y no datos personales (HU05 p.2–4). Disponible luego en la App.

## 4. Pantallas de la App UTP (simulada, móvil)

### 4.1 QR — HU06
- **Ícono QR** nuevo en la barra superior de la app (junto al carné y el correo) (HU06 p.1).
- QR grande, de alto contraste, con **brillo de pantalla al máximo** al abrirlo (**[PROPUESTA]**), listo para el lector sin imprimir (p.2).
- **Lista de vehículos autorizados** con foto en miniatura, tipo, marca, color (p.3).
- Aviso: «Código personal e intransferible» (p.4).
- QR vencido → botón «Renovar».

### 4.2 Avisos — HU22
- Push inmediato al validar el ingreso: «Ingreso registrado · Scooter Xiaomi · 16:38». **Sin ubicación del espacio** (BR-21).
- Si el ingreso fue **rechazado** → aviso informativo (p.3).
- **Historial de avisos** dentro de la app (p.2).
- Acción **«No reconozco este ingreso»** → crea incidencia para seguridad (p.4).

### 4.3 Estado general — HU23
- Push al llegar a 100 % de ocupación: «El estacionamiento de VMP está lleno».
- Pantalla con estado general: **«Hay espacios» / «Lleno»** y, a lo sumo, un porcentaje global. **Sin mapa ni casillas** (HU23 p.4, RF21).
- Interruptor «Avísame cuando haya espacio» (p.3) **[PENDIENTE brecha 7]**.

## 5. Punto de acceso (tablet) — HU07 a HU12

Pantalla única con **máquina de estados** (`/acceso`). **[PROPUESTA]**

```
ESPERANDO_QR ─lee QR─▶ VALIDANDO_QR ─ok─▶ CAPTURANDO_FOTO ─foto─▶ ANALIZANDO ─┬─ verde ─▶ INGRESO_OK (3 s) ─▶ ESPERANDO_QR
      ▲                      │                  │                            ├─ gris  ─▶ VERIFICAR (decide el guardia)
      │                      └─ error ▶ QR_ERROR (mensaje + reintentar)       └─ roja  ─▶ RECHAZADO (motivo, decisión del guardia)
      └──────────────────────────── cancelar / timeout ────────────────────────────┘
```

| Estado | Qué muestra | Reglas / HU |
|---|---|---|
| `ESPERANDO_QR` | Cámara/lector listo; **estado de dispositivos** (lector, cámara de ingreso, red, IA) con semáforo | HU07 p.2 |
| `VALIDANDO_QR` | Spinner breve; consulta usuario/matrícula | HU08 p.1–2 |
| `QR_ERROR` | **QR vencido / alterado / inexistente** con mensaje específico y qué hacer (renovar en App, ver a seguridad) | HU07 p.4, BR-07 |
| `CAPTURANDO_FOTO` | Datos del usuario y sus vehículos; **cámara de ingreso** activada solo tras leer el QR; visor con **guía de encuadre**; detección del vehículo en tiempo real y aviso «fuera de cuadro / poca luz» | HU09 p.1–2, 4 |
| `ANALIZANDO` | «Verificando tu vehículo…» (objetivo: segundos) | HU10 p.4 |
| `INGRESO_OK` | Mensaje grande y claro **«Puede ingresar»** + **cuál vehículo fue reconocido** (foto de referencia junto a la captura) | HU11 p.1–2 |
| `VERIFICAR` | Captura vs. referencias lado a lado, similitud, botones **Aprobar / Rechazar** | zona gris (docs/06) |
| `RECHAZADO` | **Motivo** visible, evidencia, botones **Rechazar ingreso / Verificación manual**; elegir **clasificación del motivo** | HU12 p.1–3 |
| `IA_NO_DISPONIBLE` | Banner «IA no disponible: modo manual»; el guardia valida visualmente y registra incidencia | RNF-03 |

Efectos al terminar: se guarda el ingreso (alimenta HU18), se dispara la notificación (HU22) y, si fue rechazo, se crea la alerta/incidencia (HU20).

**Usabilidad (tablet):** botones grandes, contraste alto, funciona al sol, mensajes ≤ 8 palabras, sonido distinto para OK/Error, accesible sin teclado.

## 6. Panel de seguridad y administración

### 6.1 Monitoreo de cámaras — HU13
- **Estado de conexión de todas las cámaras** (verde/rojo, último cuadro).
- **Cámara general del pasillo de salida**.
- Cada casilla **libre / ocupada**; **5 zonas × 8 espacios = 40**.
- Vista de cuadrícula de cámaras con snapshot actualizado cada pocos segundos.

### 6.2 Mapa de espacios — HU14, HU15, HU16, HU17
- **Indicadores generales** de ocupación (ocupados / disponibles / mantenimiento / %), HU17 p.1.
- **Ubicación exacta** por zona (plano esquemático por zona con las 8 casillas), p.2.
- **Detalle al pasar el cursor**: código, estado, última actualización, usuario y VMP si hay sesión, p.3.
- **Filtro por zona**, p.4.
- **Indicador de sincronización** con la BD (HU16 p.1) y el **recorrido del dato** cámara→IA→BD→pantallas (p.2) (puede ser un panel de “salud”).
- Los **totales se recalculan** con cada cambio (HU16 p.3). Cambio resaltado un instante (p.4: «A-02 ahora Libre»).
- Cada detección queda como **evento** con hora y confianza (HU14 p.2) — accesible desde el detalle.
- **Solo seguridad y administración** (HU17 p.5, RF21): el rol `usuario` recibe 403.

### 6.3 Incidencias — HU20 (y HU12)
- Lista con pestañas **abierta / en revisión / cerrada**, contador por estado.
- Detalle: **evidencia fotográfica** (captura vs. referencia), **responsable**, datos de la sesión.
- **Línea de tiempo** con cada acción (creada, asignada, comentada, cerrada) (p.3).
- **Cerrar** con **comentario final** obligatorio (p.4).
- Alerta en tiempo real (campana/sonido) cuando entra una `vehiculo_no_coincide`.

### 6.4 Movimientos — HU18, HU19, HU21
- **Resumen del día**: total, autorizados, rechazados (HU18 p.1); salidas del día y **siguen dentro** (HU19 p.1).
- Tabla: fecha, hora, usuario, vehículo, **resultado de la IA**, evidencia (miniatura) (HU18 p.2–3); los **intentos fallidos** también aparecen (p.4).
- Salidas automáticas desde la liberación del espacio; **permanencia** calculada (HU19 p.2–3).
- Alerta de **vehículos que no salieron al cierre** (HU19 p.4).
- **Filtros** por usuario, rango de fechas, vehículo y tipo de movimiento, **combinables**; muestra cantidad de resultados y criterio aplicado (HU21 p.1–2, 4); **exportar** CSV (p.3).

### 6.5 Reportes del piloto — HU24
- Indicadores definidos en «Testear»: **tiempo promedio de ingreso**, **número de incidencias**, **nivel de satisfacción** (p.1).
- **Gráfico** de evolución diaria del tiempo de ingreso (p.2).
- **Resultados de la encuesta** de satisfacción (p.3) **[PENDIENTE: no hay tabla de encuestas]**.
- **Selector de periodo** y **exportación** (p.4).

## 7. Textos de interfaz (mensajes oficiales) **[PROPUESTA]**

| Situación | Mensaje |
|---|---|
| Ingreso validado | «Puede ingresar. Vehículo reconocido: {marca} {tipo}.» |
| No coincide | «El vehículo no coincide con los registrados. Un agente revisará tu ingreso.» |
| QR vencido | «Tu código QR venció. Renuévalo en la App UTP.» |
| QR inválido | «Código no válido. Si el problema continúa, consulta a seguridad.» |
| Matrícula inactiva | «Tu matrícula no figura como vigente.» |
| Límite de VMP | «Ya registraste 3 vehículos. Elimina uno para agregar otro.» |
| Foto sin vehículo | «No detectamos un vehículo en la foto. Toma otra con el vehículo completo.» |
| Vehículo dentro | «Este vehículo figura dentro del estacionamiento y no puede eliminarse ahora.» |
| Lleno (push) | «El estacionamiento de VMP está lleno en este momento.» |
| Ingreso confirmado (push) | «Ingreso registrado a las {hh:mm}.» |

## 8. Accesibilidad y diseño visual **[PROPUESTA]**

- Contraste AA mínimo; íconos con texto; estados con color **y** forma (no depender solo del verde/rojo).
- Idioma: español (Perú). Hora local 24 h.
- Diseño responsivo: panel a partir de 1024 px; punto de acceso optimizado a 10"; App simulada a 390 px.
- Rendimiento: el mapa de espacios se actualiza por SSE; evitar *polling* agresivo.
- Fidelidad: los prototipos del Avance eran de **baja fidelidad**; el diseño visual definitivo es libre mientras respete los comportamientos numerados.
