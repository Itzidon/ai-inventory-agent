# Agente de Inventario con IA

Proyecto desarrollado para 4Geeks Academy — Ingeniería en IA.

## Descripción

Sistema inteligente de gestión de inventario para una tienda de suministros de cafetería.

Permite consultar productos, añadir nuevos artículos, actualizar cantidades y detectar productos con stock bajo utilizando lenguaje natural.

El sistema está compuesto por:

- **FastAPI:** API REST para gestionar el inventario.
- **Python:** implementación manual del bucle del agente.
- **Groq:** modelo de lenguaje que interpreta las peticiones del usuario.
- **CSV:** almacenamiento persistente de productos y conversaciones.

## Funcionalidades

- Consultar todos los productos.
- Añadir productos con nombre, cantidad y unidad.
- Registrar ventas y entregas.
- Actualizar cantidades de stock.
- Consultar alertas de inventario.
- Mantener el contexto de conversación durante la sesión.
- Guardar el historial en `conversation_log.csv`.

## Endpoints de la API

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/inventory` | Consultar inventario |
| POST | `/inventory` | Añadir productos |
| PATCH | `/inventory/{product_id}` | Actualizar cantidades |
| GET | `/inventory/alerts` | Consultar alertas de stock |

## Instalación

Instalar las dependencias desde la terminal:

`uv sync`

Crear un archivo `.env` en la raíz del proyecto con la siguiente variable:

`GROQ_API_KEY=tu_clave_de_groq`

El archivo `.env` está excluido del repositorio mediante `.gitignore`.

## Cómo ejecutar el proyecto

Se necesitan dos terminales abiertas.

**Terminal 1 — Iniciar la API:**

`uv run uvicorn api.app:app --reload --host 0.0.0.0 --port 8000`

Documentación de la API:

`http://localhost:8000/docs`

**Terminal 2 — Iniciar el agente:**

`uv run python agent.py`

Para detener cada proceso, pulsar `Ctrl + C`.

## Ejemplos de conversación

- ¿Qué productos tenemos en el inventario?
- Añade un producto nuevo llamado Café arábica con 15 bolsas.
- Hemos vendido 4 bolsas de café arábica.
- ¿Qué productos tienen menos de 20 unidades?

## Funcionamiento del agente

El agente utiliza un bucle programado manualmente en Python:

**Observar → Pensar → Actuar → Actualizar → Repetir**

El modelo de lenguaje selecciona las herramientas necesarias, consulta la API y utiliza los resultados para generar su respuesta.

No se utilizan frameworks de agentes como LangChain, LlamaIndex o AutoGen.

## Persistencia de datos

**products.csv**

Almacena los productos con los campos:

`id, name, quantity, unit`

**conversation_log.csv**

Registra cada evento con los campos:

`actor, message, tool_call, timestamp`

El historial se conserva entre sesiones y las nuevas conversaciones se añaden sin sobrescribir las anteriores.

## Estructura principal

- `api/app.py` — API REST con FastAPI.
- `agent.py` — Agente inteligente y herramientas.
- `products.csv` — Inventario.
- `conversation_log.csv` — Historial de conversaciones.
- `pyproject.toml` — Dependencias del proyecto.
- `.gitignore` — Exclusiones de Git.

## Autoría

Proyecto realizado por Itzidon para 4Geeks Academy.