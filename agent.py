
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from openai import OpenAI

# Configuración
load_dotenv()

API_URL = "http://127.0.0.1:8000"
LOG_FILE = Path(__file__).resolve().parent / "conversation_log.csv"
MODEL = "openai/gpt-oss-120b"

# Instrucciones para el agente
SYSTEM_PROMPT = (
    "Eres el asistente de inventario de Carla, de una tienda "
    "de suministros para cafeterías. "
    "Responde siempre en español y de manera clara. "
    "Usa las herramientas para consultar o modificar el inventario. "
    "No inventes datos. "
    "Antes de actualizar un producto existente, consulta el inventario "
    "para encontrar su ID. "
    "Si hay varios productos con el mismo nombre, pide a Carla "
    "que aclare cuál desea modificar. "
    "Para registrar entregas de productos existentes, usa actualizar_stock "
    "con delta positivo. "
    "Para registrar ventas, usa actualizar_stock con delta negativo. "
    "Para productos nuevos, usa agregar_producto. "
    "Si una herramienta devuelve un error, explícalo sin afirmar "
    "que el inventario se ha modificado."
)

# Herramientas disponibles para el LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_inventario",
            "description": "Consulta todos los productos con ID, nombre, cantidad y unidad.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "agregar_producto",
            "description": "Añade un producto NUEVO al inventario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit": {"type": "string"}
                },
                "required": ["name", "quantity", "unit"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_stock",
            "description": "Suma o resta stock de un producto usando su ID y un delta.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "delta": {"type": "number"}
                },
                "required": ["product_id", "delta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_alertas",
            "description": "Consulta productos con stock inferior a un umbral.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {"type": "number"}
                },
                "required": []
            }
        }
    }
]


# Guardar cada evento de la conversación
def registrar(actor, message, tool_call=""):
    nuevo = not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as archivo:
        writer = csv.writer(archivo)

        if nuevo:
            writer.writerow(["actor", "message", "tool_call", "timestamp"])

        writer.writerow([
            actor,
            message,
            tool_call,
            datetime.now(timezone.utc).isoformat()
        ])


# Comunicarse con nuestra API FastAPI
def llamar_api(method, path, data=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None

    request = Request(
        f"{API_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method=method
    )

    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    except HTTPError as error:
        return {
            "error": f"HTTP {error.code}",
            "detail": error.read().decode("utf-8")
        }

    except URLError as error:
        return {
            "error": f"No se pudo conectar con la API: {error.reason}"
        }


# Ejecutar la herramienta elegida por el LLM
def ejecutar_tool(name, args):
    try:
        if name == "consultar_inventario":
            return llamar_api("GET", "/inventory")

        if name == "agregar_producto":
            return llamar_api("POST", "/inventory", {
                "name": args["name"],
                "quantity": args["quantity"],
                "unit": args["unit"]
            })

        if name == "actualizar_stock":
            return llamar_api(
                "PATCH",
                f"/inventory/{int(args['product_id'])}",
                {"delta": args["delta"]}
            )

        if name == "consultar_alertas":
            threshold = float(args.get("threshold", 10))
            return llamar_api(
                "GET",
                f"/inventory/alerts?threshold={threshold}"
            )

        return {"error": f"Herramienta desconocida: {name}"}

    except (KeyError, ValueError, TypeError) as error:
        return {"error": f"Parámetros inválidos: {error}"}


# Bucle del agente:
# Observar -> Pensar -> Actuar -> Actualizar -> Repetir
def responder(client, mensajes):

    for _ in range(10):
        response = client.chat.completions.create(
            model=MODEL,
            messages=mensajes,
            tools=TOOLS,
            tool_choice="auto"
        )

        assistant = response.choices[0].message

        # Si no hay tools pendientes, respuesta final
        if not assistant.tool_calls:
            texto = assistant.content or "No he podido generar una respuesta."

            mensajes.append({
                "role": "assistant",
                "content": texto
            })

            registrar("agent", texto)
            return texto

        # Guardar las llamadas a herramientas en memoria
        mensajes.append({
            "role": "assistant",
            "content": assistant.content or "",
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    }
                }
                for call in assistant.tool_calls
            ]
        })

        # Ejecutar las herramientas solicitadas
        for call in assistant.tool_calls:
            nombre = call.function.name

            registrar("agent", call.function.arguments, nombre)

            try:
                argumentos = json.loads(call.function.arguments)
                resultado = ejecutar_tool(nombre, argumentos)

            except (ValueError, TypeError) as error:
                resultado = {
                    "error": f"Argumentos JSON inválidos: {error}"
                }

            texto_resultado = json.dumps(
                resultado,
                ensure_ascii=False
            )

            registrar("tool", texto_resultado, nombre)

            # Devolver el resultado al contexto del LLM
            mensajes.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": texto_resultado
            })

    texto = "No he podido completar la tarea tras varios pasos."

    mensajes.append({
        "role": "assistant",
        "content": texto
    })

    registrar("agent", texto)
    return texto


# Interfaz de conversación desde la terminal
def main():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("Falta GROQ_API_KEY en el archivo .env")
        return

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    mensajes = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    print("Agente de inventario listo.")
    print("Escribe 'salir' para terminar.\n")

    while True:
        try:
            entrada = input("Carla: ").strip()

        except (EOFError, KeyboardInterrupt):
            print("\nHasta pronto")
            break

        if entrada.lower() in ("salir", "exit", "quit"):
            print("Hasta pronto")
            break

        if not entrada:
            continue

        mensajes.append({
            "role": "user",
            "content": entrada
        })

        registrar("user", entrada)

        try:
            respuesta = responder(client, mensajes)
            print(f"\nAgente: {respuesta}\n")

        except Exception as error:
            print(f"\nError al consultar Groq: {error}\n")


if __name__ == "__main__":
    main()
