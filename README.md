# Acopio — Sistema de Gestión de Donaciones

> Hackathon 2026 · Equipo **ByteForce**

---

## Descripción del proyecto

**Acopio** es una plataforma web para la gestión integral de centros de acopio de donaciones en México. Permite registrar, rastrear y redistribuir artículos donados entre múltiples centros de recolección, campañas y organizaciones receptoras, todo en tiempo real y con roles diferenciados por tipo de usuario.

### Diferenciador principal — Redistribución automática inteligente

El sistema analiza continuamente el inventario de todos los centros activos y detecta desequilibrios automáticamente: un centro con excedente de un artículo y otro con escasez del mismo. Genera **sugerencias de transferencia** que el coordinador aprueba con un solo clic, sin reportes manuales ni comunicación externa al sistema. Además integra un **mapa interactivo** (Leaflet + OpenStreetMap) en el formulario de transferencia y **geocodificación real** de direcciones mexicanas en el alta de centros.

---

## Problema que resuelve e impacto

### Problema
Los centros de acopio en México operan de forma aislada: uno acumula arroz mientras otro carece de él, sin mecanismo para detectarlo ni corregirlo rápido. La coordinación se hace por teléfono o WhatsApp, los inventarios en papel o Excel, y las pérdidas por merma no tienen trazabilidad ni aprobación formal.

### A quién beneficia

| Actor | Beneficio |
|---|---|
| **Coordinadores generales** | Visibilidad total, aprobación de mermas, redistribución automática con 1 clic |
| **Encargados de centro** | Inventario en tiempo real de su centro, registro rápido de movimientos |
| **Voluntarios** | Formulario de recepción con registro de donante |
| **Instituciones receptoras** | Confirmación digital de entregas recibidas |
| **Beneficiarios finales** | Reciben artículos más rápido gracias a la redistribución equitativa |

---

## Alcance del MVP — Checklist de criterios de aceptación

### Implementado ✅

- [x] Autenticación por rol con sesión persistente (`localStorage`)
- [x] 5 dashboards diferenciados: coordinador, encargado, voluntario, institución, líder de campaña
- [x] Registro completo de movimientos: recepción con donante, entrega a institución, transferencia entre centros, merma y ajuste manual
- [x] Inventario automático por centro y campaña (client-side aggregation sin N+1 queries)
- [x] Flujo de aprobación de mermas: encargado registra → coordinador aprueba/rechaza
- [x] Confirmación de entregas por parte de las instituciones receptoras
- [x] CRUD completo de centros, campañas, artículos y usuarios desde el coordinador
- [x] **Mapa interactivo** en formulario de transferencia (Leaflet + OSM) con selección bidireccional mapa ↔ dropdown
- [x] **Geocodificación real** (Nominatim) en modal de alta de centros: dirección estructurada mexicana + pin arrastrable
- [x] 4 centros de ejemplo con coordenadas reales en México (CDMX, Guadalajara, Monterrey)
- [x] **Redistribución automática**: detección de desequilibrios y sugerencias con aprobación en 1 clic
- [x] Exportación CSV de movimientos con filtros aplicados (compatible Excel con BOM UTF-8)
- [x] Metas de recolección por campaña con barra de progreso
- [x] Top 7 artículos más donados con visualización de barras
- [x] Modo oscuro / claro persistente
- [x] Dashboard del encargado con info de su centro, KPIs de entradas/salidas/mermas e historial reciente

### No implementado (fuera de alcance) ❌

- [ ] Hash de contraseñas — actualmente texto plano (solo demo)
- [ ] WebSockets para sincronización multi-usuario en tiempo real
- [ ] Notificaciones push por correo / SMS
- [ ] Foto de artículos o recibos
- [ ] Paginación server-side del historial de movimientos
- [ ] Aplicación móvil nativa

---

## Stack utilizado

| Capa | Tecnología |
|---|---|
| **Backend** | Python 3.13 · Flask 3.1 · Flask-CORS |
| **Base de datos** | SQLite 3 (modo WAL, sin ORM — queries directas) |
| **Frontend** | HTML5 · CSS3 · JavaScript vanilla (ES2022), sin frameworks |
| **Mapas** | Leaflet.js 1.9.4 · OpenStreetMap tiles |
| **Geocodificación** | Nominatim API pública (OpenStreetMap) |
| **Diseño** | Sistema de diseño propio: glassmorphism, CSS custom properties, modo oscuro/claro |
| **Seed de datos** | JSON estáticos en `/data/` migrados a SQLite en el primer arranque |

---

## Herramientas de IA utilizadas

| Herramienta | Uso en el proyecto |
|---|---|
| **Claude (Anthropic)** | Generación y refactorización del código backend (Flask, SQLite), dashboards HTML/JS, sistema de roles, algoritmo de redistribución automática, integración de mapas Leaflet/Nominatim, estructura de este README |
| **Claude** | Revisión de lógica de negocio: flujo de mermas con `confirmado` flag, sincronización mapa↔dropdown, cálculo client-side de stock por centro |

> Todo el código fue revisado, probado e integrado por el equipo. La IA fue usada como herramienta de asistencia, no como reemplazo del criterio de ingeniería del equipo.

---

## Instalación y ejecución

### Requisitos
- Python 3.10 o superior
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/<tu-usuario>/acopio.git
cd acopio

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Arrancar el servidor
python app.py
```

Abre `http://localhost:5000` en tu navegador.

En el **primer arranque** se crea automáticamente `data/acopio.db` y se puebla con los datos seed de `/data/*.json`. No se requiere ninguna configuración adicional.

> `data/acopio.db` está en `.gitignore`. Cada clon parte de cero con los datos de ejemplo.

---

## Cuentas de acceso para pruebas

| Rol | Usuario | Contraseña | Dashboard |
|---|---|---|---|
| Coordinador general | `ana_coord` | `coord2026` | Overview, redistribución, mermas, gestión completa |
| Encargado Centro Norte CDMX | `carlos_enc` | `norte2026` | Inventario y movimientos de su centro |
| Encargado Centro Guadalajara | `u1x` | `1234` | Inventario y movimientos de su centro |
| Encargado Centro Monterrey | `u2x` | `1234` | Inventario y movimientos de su centro |
| Voluntario | `sofia_vol` | `vol2026` | Recepciones y entregas (Centro Sur CDMX) |
| Institución receptora | `hospital_civil` | `hosp2026` | Confirmar entregas recibidas |
| Líder de campaña | `marco_lider` | `camp2026` | Vista de campaña activa |

### Flujo recomendado para probar

1. **Coordinador** (`ana_coord`) → ver overview con KPIs, redistribución automática y mermas pendientes
2. **Registrar recepción** en la pestaña "Registrar" del coordinador (artículo + donante)
3. **Registrar transferencia** → ver el mapa con los 4 centros en México, seleccionar destino desde el mapa o el dropdown
4. **Crear un centro nuevo** → llenar dirección real (ej: `Av. Reforma 222, Col. Juárez, 06600, Ciudad de México, CDMX`) → clic "Buscar en el mapa" → ajustar pin → guardar
5. **Encargado** (`carlos_enc`) → ver su dashboard con KPIs de flujo e historial reciente
6. **Registrar una merma** desde el encargado → volver al coordinador y aprobarla
7. **Institución** (`hospital_civil`) → confirmar una entrega pendiente

---

## Estructura del repositorio

```
acopio/
├── app.py                       # Servidor Flask — todas las rutas REST
├── requirements.txt
├── .gitignore
├── README.md
│
├── shared.css                   # Sistema de diseño: tokens, componentes, glassmorphism
├── shared.js                    # Auth, helpers, TIPO_MAP, toast, autocomplete de artículos
├── login.html                   # Pantalla de acceso unificada (todos los roles)
│
├── dashboard_coordinador.html   # Rol: coordinador_general
├── dashboard_encargado.html     # Rol: encargado_centro
├── dashboard_voluntario.html    # Rol: voluntario
├── dashboard_institucion.html   # Rol: institucion_receptora
├── dashboard_lider.html         # Rol: lider_campana
│
├── database/
│   ├── __init__.py
│   └── sqlite_db.py             # Única capa de datos: esquema, migraciones, todas las queries
│
└── data/
    ├── articulos.json           # Seed: catálogo de artículos por categoría
    ├── campanas.json            # Seed: campañas de recolección
    ├── centros.json             # Seed: 4 centros en México con coords y dirección real
    ├── instituciones.json       # Seed: instituciones receptoras
    ├── movimientos.json         # Seed: movimientos de ejemplo
    └── usuarios.json            # Seed: un usuario por rol
```

---

## Fuentes y dependencias externas

| Recurso | Tipo | URL |
|---|---|---|
| Flask | Framework web Python (BSD-3) | https://flask.palletsprojects.com |
| Flask-CORS | Middleware CORS (MIT) | https://flask-cors.readthedocs.io |
| Leaflet.js 1.9.4 | Librería de mapas (BSD-2) | https://leafletjs.com |
| OpenStreetMap | Tiles de mapa (CC BY-SA 2.0) | https://openstreetmap.org/copyright |
| Nominatim | API de geocodificación (ODbL) | https://nominatim.openstreetmap.org |
| SQLite | Base de datos embebida (dominio público) | https://sqlite.org |

---

## Limitaciones conocidas

| Limitación | Impacto | Solución futura |
|---|---|---|
| Contraseñas en texto plano | Solo apto para demo/dev | bcrypt + salting en registro |
| Sin sincronización multi-tab | Inconsistencia de UI si dos usuarios editan a la vez | WebSockets o polling periódico |
| Nominatim rate limit (1 req/s) | El geocodificador puede fallar bajo carga | Caché local + debounce |
| Sin paginación en historial | Puede ser lento con miles de movimientos | Paginación server-side con OFFSET/LIMIT |
| SQLite en archivo local | No escala a múltiples instancias del servidor | PostgreSQL en producción |
| Sin HTTPS | Datos en texto plano en tránsito | Nginx + Let's Encrypt en deploy |
| Redistribución sin umbral configurable | El umbral del 2.5× está hardcoded | Panel de configuración por artículo |

---

## Pasos futuros

- [ ] Hash de contraseñas (bcrypt) y tokens JWT para sesión segura
- [ ] Paginación y búsqueda server-side en historial de movimientos
- [ ] Notificaciones por correo (Flask-Mail) cuando hay mermas pendientes o stock crítico
- [ ] Umbral de redistribución configurable por artículo desde el coordinador
- [ ] Dashboard público de transparencia (qué se recibió y distribuyó por campaña)
- [ ] Escaneo QR / código de barras para registro rápido
- [ ] Deploy en Railway o Render con PostgreSQL

---

## Capturas de la demo

> Las capturas se encuentran en la carpeta `/screenshots/` del repositorio o en la presentación del hackathon.

Pantallas principales:
- Login unificado por rol
- Overview del coordinador: KPIs, flujo global, sugerencias de redistribución y mermas pendientes
- Mapa interactivo de transferencia con los 4 centros en México
- Modal de alta de centro con geocodificación real y pin arrastrable
- Dashboard del encargado: info de su centro, KPIs de entradas/salidas/mermas e historial reciente
- Vista de institución: confirmación de entregas pendientes

---

## Reparto de trabajo del equipo *(opcional)*

| Miembro | Área principal |
|---|---|
| *(nombre)* | Backend Flask, modelo de datos SQLite, endpoints REST |
| *(nombre)* | Frontend: dashboards coordinador y encargado, sistema de diseño |
| *(nombre)* | Frontend: dashboards voluntario, institución y líder, integración Leaflet |
| *(nombre)* | Algoritmo de redistribución, geocodificación Nominatim, integración y pruebas |

---

https://aegis-vmz2.onrender.com/

*Proyecto desarrollado para Hackathon 2026 · Licencia MIT*
