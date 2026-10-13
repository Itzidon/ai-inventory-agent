
import csv
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# Crear la aplicación
app = FastAPI(title="Agente de Inventario con IA")

# Archivo donde guardaremos los productos
PRODUCTS_FILE = Path(__file__).resolve().parent.parent / "products.csv"

COLUMNAS = ["id", "name", "quantity", "unit"]


# Modelo para añadir nuevos productos
class ProductoNuevo(BaseModel):
    name: str = Field(min_length=1)
    quantity: float = Field(ge=0, allow_inf_nan=False)
    unit: str = Field(min_length=1)


# Modelo para actualizar cantidades
class ActualizarStock(BaseModel):
    delta: float = Field(allow_inf_nan=False)


# Endpoint de inicio
@app.get("/")
def inicio():
    return {
        "mensaje": "API de inventario funcionando correctamente"
    }


# Consultar todos los productos
@app.get("/inventory")
def listar_inventario():

    # Crear el CSV si todavía no existe
    if not PRODUCTS_FILE.exists():
        with open(
            PRODUCTS_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as archivo:
            writer = csv.writer(archivo)
            writer.writerow(COLUMNAS)

    # Leer los productos guardados
    with open(
        PRODUCTS_FILE,
        "r",
        newline="",
        encoding="utf-8"
    ) as archivo:
        productos = list(csv.DictReader(archivo))

    # Convertir los datos a números
    for producto in productos:
        producto["id"] = int(producto["id"])
        producto["quantity"] = float(producto["quantity"])

    return productos


# Añadir un nuevo producto
@app.post("/inventory", status_code=201)
def agregar_producto(producto: ProductoNuevo):

    productos = listar_inventario()

    # Calcular el siguiente ID disponible
    nuevo_id = max(
        (p["id"] for p in productos),
        default=0
    ) + 1

    nuevo_producto = {
        "id": nuevo_id,
        "name": producto.name,
        "quantity": producto.quantity,
        "unit": producto.unit
    }

    # Guardar el nuevo producto en el CSV
    with open(
        PRODUCTS_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=COLUMNAS
        )
        writer.writerow(nuevo_producto)

    return nuevo_producto


# Actualizar stock: sumar o restar cantidades
@app.patch("/inventory/{product_id}")
def actualizar_stock(
    product_id: int,
    cambio: ActualizarStock
):

    productos = listar_inventario()

    for producto in productos:

        if producto["id"] == product_id:

            cantidad_actual = producto["quantity"]
            nueva_cantidad = cantidad_actual + cambio.delta

            # Evitar cantidades negativas
            if nueva_cantidad < 0:
                raise HTTPException(
                    status_code=400,
                    detail="No hay suficiente stock disponible"
                )

            # Actualizar cantidad
            producto["quantity"] = nueva_cantidad

            # Guardar el inventario actualizado
            with open(
                PRODUCTS_FILE,
                "w",
                newline="",
                encoding="utf-8"
            ) as archivo:
                writer = csv.DictWriter(
                    archivo,
                    fieldnames=COLUMNAS
                )
                writer.writeheader()
                writer.writerows(productos)

            return producto

    # Producto inexistente
    raise HTTPException(
        status_code=404,
        detail="Producto no encontrado"
    )


# Consultar productos con stock bajo
@app.get("/inventory/alerts")
def alertas_inventario(
    threshold: float = 10
):

    # Validar el umbral
    if not 0 <= threshold < float("inf"):
        raise HTTPException(
            status_code=400,
            detail="El umbral debe ser un número finito y no negativo"
        )

    productos = listar_inventario()

    # Seleccionar productos por debajo del umbral
    alertas = [
        producto
        for producto in productos
        if producto["quantity"] < threshold
    ]

    return alertas
