# 27 · Guía para probar todo y grabar el video

Ruta completa, de la preparación a la grabación: dejar los datos en cero, ensayar con una lista de comprobación y grabar el video escena por escena (qué se presiona, qué se dice y cuánto dura).

> **Estado al 17-nov-2026:** el guion completo de §5 se ensayó de forma automática en Edge con una **cámara simulada** (un video con el QR y luego el vehículo), contra la IA real y con datos limpios. Las cinco escenas salieron bien. **Falta** ensayarlo con la cámara USB, el celular y los vehículos reales: haz la lista de §4 antes de grabar.

## 1. Preparación (el día anterior)

| Qué | Detalle |
|---|---|
| **Quién hace qué** | Un **usuario con scooter** (en el guion, Diego), un **usuario con bicicleta** (Valeria), alguien que haga de **guardia** y alguien que **graba y narra** |
| **Vehículos** | El scooter de verdad. Para la escena 4 basta con que Valeria tenga registrada una bicicleta: el scooter que llega al punto de acceso no es el suyo |
| **Fotos de referencia** | Con el celular, **antes**: cada vehículo **completo, de costado, con buena luz**, en el mismo lugar donde estará la cámara del punto de acceso. Pásalas a la laptop |
| **Una foto «equivocada»** | Una foto de una bicicleta, para mostrar que la IA rechaza una foto que no corresponde al tipo registrado |
| **Cámara USB** | Conectada a la laptop, apuntando a donde se pondrá el vehículo, a la altura del manubrio |
| **Celular** | En la **misma Wi-Fi** que la laptop, con brillo al máximo. Solo muestra el QR: no usa su cámara |
| **Pesos del modelo** | `ia_service/pesos/E2-3clases-best.pt` (no están en Git) |
| **Grabar la pantalla** | OBS Studio, o la Xbox Game Bar de Windows (`Win + Alt + R`). El celular se graba con otra cámara o se muestra a la cámara USB |

## 2. Dejar los datos en cero y levantar todo

Con Docker Desktop abierto, en PowerShell:

```powershell
cd C:\Users\gianc\vmp-utp
.\scripts\reiniciar-demo.ps1
```

Pide escribir `SI`, borra los vehículos, fotos e ingresos, deja libres los 40 espacios, levanta el sistema y al final muestra:

```
Listo. Datos de la demo en cero.
  Base de datos : ok
  IA            : disponible (E2-3clases)
  Espacios      : 40 de 40 libres
  Vehiculos     : ninguno: se registran en el Portal
```

- **Los perfiles se mantienen:** los mismos 6 perfiles UTP y 3 guardias, para iniciar sesión igual que siempre. Empiezan **sin vehículos y sin consentimiento aceptado**: todo se hace frente a la cámara.
- Opciones: `-ConEjemplos` (perfiles con vehículos de ejemplo con fotos dibujadas, para probar rápido) y `-SinIA` (sin el detector real).
- No toca los pesos ni la base de pruebas.
- **Apagar** sin borrar (libera memoria): `docker compose --profile ia down`.
- **Volver a encender** sin borrar: `$env:DB_PUERTO="55433"; $env:IA_MODO="http"; docker compose --profile ia up -d`.

Antes de grabar cierra Discord, juegos y pestañas: con 8 GB de RAM, Docker se cae si falta memoria.

## 3. Direcciones

| Interfaz | En la laptop | En el celular |
|---|---|---|
| Portal UTP | <http://localhost:5173/portal> | — |
| App UTP (QR) | <http://localhost:5173/app> | `http://<IP de la laptop>:5173/app` |
| Punto de acceso | <http://localhost:5173/acceso> | — |
| Monitoreo de espacios | <http://localhost:5173/espacios> | — |

**IP de la laptop:** en PowerShell, `ipconfig` → «Dirección IPv4» de la Wi-Fi (por ejemplo `192.168.1.34`).

Si el celular no carga la página:

1. Comprueba que los dos estén en la misma Wi-Fi.
2. En Windows, la red Wi-Fi debe ser **privada** (Configuración → Red e Internet → Wi-Fi → propiedades).
3. Permite Docker Desktop en el Firewall de Windows para redes privadas.

La cámara del punto de acceso se usa en la laptop (`localhost`): el navegador solo permite la cámara en `localhost` o en `https://`.

## 4. Ensayo: lista de comprobación

Hazla completa una vez y luego vuelve a dejar los datos en cero (§2) antes de grabar.

| # | Qué haces | Qué debe pasar |
|---|---|---|
| 1 | Abres `/portal` | Pantalla «Inicia sesión» con 6 perfiles de ejemplo |
| 2 | Escribes `U99999999` y pulsas **Ingresar** | «No encontramos ese código UTP» |
| 3 | Entras como Diego | La casilla de consentimiento está **sin marcar** |
| 4 | Registras el scooter y subes la foto de la bicicleta | Rechazada: «La foto muestra bicicleta, pero registraste scooter eléctrico» |
| 5 | Subes la foto del scooter | «Tu QR de acceso está disponible en la App UTP» |
| 6 | Abres la App en el **celular** con el código de Diego | QR «Vigente» con su nombre |
| 7 | Abres `/acceso`, eliges al guardia y la cámara USB | El video de la cámara se ve en pantalla |
| 8 | Acercas el QR del celular a la cámara | Pasa solo a «IA en vivo» |
| 9 | Pones el scooter frente a la cámara | Caja con clase, confianza y semejanza; luego **«✓ Puede ingresar · Espacio asignado A-01»** |
| 10 | Abres `/espacios` | 39 libres; A-01 en rojo con «Diego» |
| 11 | Registras la bicicleta de Valeria y lees su QR con el scooter delante | **«El vehículo no coincide»**; escribes un motivo y pulsas **Rechazar** |
| 12 | En `/espacios`, pulsas A-01 y **Registrar salida y liberar** | 40 libres |

Si la semejanza del paso 9 no llega al 70 %, la foto de referencia y la toma en vivo son demasiado distintas (fondo, luz, ángulo). Vuelve a tomar la foto de referencia en el mismo lugar que la cámara. No bajes el umbral para el video.

## 5. Guion del video (unos 5 minutos)

Datos en cero (§2) antes de empezar. La columna «Qué se dice» es una sugerencia de narración.

| # | Escena y pantalla | Qué se presiona | Qué se dice | Duración |
|---|---|---|---|---|
| 0 | **Presentación** (el estacionamiento, o una diapositiva) | — | «En la Torre Arequipa el ingreso de VMP es manual: hay colas y no se puede verificar de quién es cada vehículo. Proponemos registrarlo una vez y validarlo con un QR y con IA.» | 0:20 |
| 1 | **Portal UTP** (laptop) | Perfil de Diego → marca el consentimiento → **Continuar a mis vehículos** → **+ Agregar** → Scooter eléctrico, marca, color → **Guardar y continuar** | «El estudiante entra al Portal UTP, acepta el tratamiento de sus datos y registra su scooter. Puede registrar hasta 3 vehículos.» | 0:40 |
| 1b | **Portal**: foto de referencia | Sube la foto de la **bicicleta** → **Validar foto** → rechazada. Sube la foto del **scooter** → **Validar foto** → aceptada | «Al subir la foto, la IA comprueba que de verdad muestra un vehículo del tipo registrado. Esta es una bicicleta, así que la rechaza. Con la foto correcta, el QR queda listo.» | 0:30 |
| 2 | **App UTP** (celular) | Escribe el código de Diego → **Ingresar** | «En la App UTP aparece su QR personal, con vigencia por ciclo académico. El QR no contiene datos personales.» | 0:20 |
| 3 | **Punto de acceso** (laptop y cámara USB) | Elige al guardia → acerca el QR a la cámara → el scooter frente a la cámara | «El guardia solo acerca el QR a la cámara. La IA analiza el video en vivo: detecta que es un scooter y lo compara con la foto registrada. Al superar los mínimos en varios cuadros seguidos, valida el ingreso y le asigna un espacio, aquí el A-01.» | 0:50 |
| 4 | **Monitoreo** | Pulsa «39 de 40 espacios libres ›» | «Seguridad ve en tiempo real cuántos espacios hay libres y quién ocupa cada uno. Esta vista es solo para seguridad: el usuario nunca ve el mapa.» | 0:25 |
| 5 | **Punto de acceso**: caso que decide el guardia | Vuelve a «Punto de acceso» → Valeria acerca su QR → el **scooter** frente a la cámara → escribe el motivo → **Rechazar** | «Valeria tiene registrada una bicicleta, pero llega con un scooter. La IA detecta que no coincide, y no decide sola: el guardia revisa las fotos, escribe el motivo y rechaza. Todo queda registrado con evidencia.» | 0:45 |
| 6 | **Monitoreo**: salida | Pulsa A-01 → **Registrar salida y liberar** | «Al salir, el espacio se libera. Hoy lo marca el guardia; en la siguiente fase lo harán cámaras en cada zona.» | 0:20 |
| 7 | **Cierre** | — | Siguiente fase (§6) y límites honestos (§6) | 0:30 |

**Consejos para grabar**

- Tras «Puede ingresar», la pantalla vuelve a «Leer QR» a los 5 segundos: narra el espacio asignado mientras se ve, o pausa al editar.
- Si el QR no se deja leer en la toma, en «Leer QR» usa **«Solo para la demo, QR de…» → simular la lectura del QR**.
- **Para repetir una toma de la escena 3:** el vehículo ya figura «dentro». Libéralo en el monitoreo, o pulsa **registrar la salida de sus vehículos** en «Leer QR». Si no, el siguiente intento va a «Revisa y decide».
- Graba cada escena por separado y únelas al editar: es más fácil repetir solo la que salió mal.

## 6. Qué decir sobre la IA

- La IA **no mira todo el tiempo**: empieza a analizar cuando se leyó un QR válido, y solo el video de ese ingreso.
- Usa dos modelos:
  - el **detector YOLO26** (`E2-3clases`) dice si hay un VMP y si es scooter, bicicleta o moto eléctrica;
  - un **comparador de imágenes** mide cuánto se parece a la foto que el usuario registró.
- Si los dos superan su mínimo en 3 cuadros seguidos, el ingreso se valida solo. Si no, **decide un humano**: la IA nunca rechaza de forma definitiva.
- Cada decisión guarda la foto, la clase, la confianza y la semejanza como evidencia, también los intentos fallidos.
- **Límites, dichos con honestidad:**
  - La semejanza compara la imagen completa (forma, color, fondo), no reconoce «este scooter exacto»: dos modelos iguales del mismo color se parecen mucho.
  - Los mínimos (60 % y 70 %) y los números 3 cuadros y 8 s son **provisionales**: se medirán con fotos propias tomadas en la Torre Arequipa.
  - Las métricas del detector están en `ia_service/resultados/`. No uses otras cifras en el video.

### La siguiente fase: cámaras que vigilan los espacios

Hoy el espacio se asigna al validar el ingreso y la salida la marca el guardia. En la siguiente fase (HU13–HU16), **cámaras fijas en el techo de cada zona** harán ese trabajo solas:

1. **Delimitar cada espacio en el piso** con cinta o pintura de alto contraste. Ayuda al usuario a estacionar dentro del espacio y le da a la cámara bordes claros.
2. **Calibrar una vez cada cámara:** sobre su imagen se marca el polígono de cada espacio (la base ya tiene el campo `roi_json` por espacio para guardarlo). Unas **marcas impresas** (patrones tipo ArUco) en las esquinas permiten recalibrar solo si la cámara se mueve un poco. La cinta ayuda, pero no es imprescindible: el polígono también se puede dibujar a mano sobre la imagen.
3. **Detectar:** el mismo detector YOLO26 busca VMP en la imagen de la zona. Un espacio está **ocupado** si un vehículo detectado cae dentro de su polígono.
4. **Evitar falsos cambios:** la ocupación se confirma tras varios cuadros seguidos y la liberación tras un tiempo de espera (alguien que pasa caminando no cuenta). Solo los **cambios** de estado se registran.
5. **Cruzar con el ingreso:** si el vehículo ocupa el espacio que se le asignó, se confirma. Si se estacionó en otro, el sistema actualiza el espacio o avisa al guardia. Al irse, la cámara libera el espacio y registra la salida, sin que el guardia toque nada.

El monitoreo que hoy se ve en `/espacios` es el mismo que entonces se actualizará solo.

## 7. Si algo falla

| Síntoma | Qué hacer |
|---|---|
| Indicador **IA** en rojo | `docker compose restart ia_service` y espera un minuto. Mientras, el guardia puede decidir a mano |
| «No se pudo abrir la cámara» | Cierra otras apps que la usen (Teams, Zoom, la app Cámara); revisa el permiso en el candado de la barra de direcciones |
| Se abre la cámara equivocada | Menú **Cámara** arriba a la derecha del punto de acceso |
| El QR no se lee | Más brillo, acerca o aleja el celular; o «simular la lectura del QR» |
| La IA nunca ve el vehículo | Más luz, vehículo completo dentro del cuadro, de costado; o «¿Sin cámara? Subir una foto» |
| La semejanza no llega al 70 % | Toma la foto de referencia en el mismo lugar, con la misma luz y el mismo ángulo que la cámara |
| «Estacionamiento lleno» | Libera espacios en `/espacios`, o deja los datos en cero (§2) |
| Docker se cerró solo | Falta de memoria: cierra programas, reinicia Docker Desktop y vuelve a encender (§2) |

## 8. ¿Hace falta un APK?

No. La «App UTP» es una página web: en el proyecto real sería una sección dentro de la app oficial de la UTP, que no construimos. Para el video basta abrirla en el navegador del celular.

## 9. Publicar en Railway y Vercel (opcional, no hecho)

Para el video no hace falta: en local es gratis, la IA responde rápido y no se expone nada. Si se quiere una dirección pública:

| Pieza | Dónde | Cómo |
|---|---|---|
| Base de datos | Railway | Plantilla PostgreSQL |
| Backend | Railway | Carpeta `backend/` con su `Dockerfile`; un volumen para `MEDIA_ROOT` (fotos); `CORS_ORIGENES` con la URL de Vercel |
| IA | Railway | Carpeta `ia_service/` con su `Dockerfile`; usa unos 700 MB de memoria: revisa el límite del plan |
| Frontend | Vercel | Carpeta `frontend/`; `VITE_API_URL` = URL pública del backend; reescribir `/portal`, `/app`, `/acceso` y `/espacios` a `index.html` |

Antes hay que resolver:

1. Subir el repositorio a GitHub.
2. Hacer llegar los pesos (`best.pt` no va en Git), por ejemplo como archivo de un *Release* que la IA descargue al arrancar.
3. **Seguridad:** el inicio de sesión sin contraseña solo existe con `ENTORNO=dev`. Publicado así, cualquiera con la dirección entra como cualquier perfil o guardia. Es aceptable solo con datos ficticios y apagándolo después de la demo.

A cambio, con `https://` la cámara funcionaría también en un celular o una tablet.
