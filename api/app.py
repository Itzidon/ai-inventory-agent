
import csv
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Crear la aplicación
app = FastAPI(title="Agente de Inventario con IA")

# Archivo donde guardaremos los productos
PRODUCTS_FILE = Path(__file__).resolve().parent.parent / "products.csv"


# Modelo para añadir productos
class ProductoNuevo(BaseModel):
    name: str = Field(min_length=1)
    quantity: float = Field(ge=0, allow_inf_nan=False)
    unit: str = Field(min_length=1)


# Modelo para actualizar el stock
class ActualizarStock(BaseModel):
    delta: float = Field(allow_inf_nan=False)


# Endpoint de inicio
@app.get("/")
def inicio():
    return {"mensaje": "API de inventario funcionando correctamente"}


# Consultar todos los productos
@app.get("/inventory")
def listar_inventario():
    if not PRODUCTS_FILE.exists():
        with open(PRODUCTS_FILE, "w", newline="", encoding="utf-8") as archivo:
            writer = csv.writer(archivo)
            writer.writerow(["id", "name", "quantity", "unit"])

    with open(PRODUCTS_FILE, "r", encoding="utf-8", newline="") as archivo:
        productos = list(csv.DictReader(archivo))

    return productos


# Añadir un nuevo producto
@app.post("/inventory", status_code=201)
def agregar_producto(producto: ProductoNuevo):
    productos = listar_inventario()

    nuevo_id = max(
        (int(p["id"]) for p in productos),
        default=0
    ) + 1

    nuevo_producto = {
        "id": nuevo_id,
        "name": producto.name,
        "quantity": producto.quantity,
        "unit": producto.unit
    }

    with open(PRODUCTS_FILE, "a", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=["id", "name", "quantity", "unit"]
        )
        writer.writerow(nuevo_producto)

    return nuevo_producto


# Actualizar la cantidad de un producto
@app.patch("/inventory/{product_id}")
def actualizar_stock(product_id: int, cambio: ActualizarStock):
    productos = listar_inventario()

    for producto in productos:
        if int(producto["id"]) == product_id:

            cantidad_actual = float(producto["quantity"])
            nueva_cantidad = cantidad_actual + cambio.delta

            if nueva_cantidad < 0:
                raise HTTPException(
                    status_code=400,
                    detail="No hay suficiente stock disponible"
                )

            producto["quantity"] = nueva_cantidad

            with open(PRODUCTS_FILE, "w", newline="", encoding="utf-8") as archivo:
                writer = csv.DictWriter(
                    archivo,
                    fieldnames=["id", "name", "quantity", "unit"]
                )
                writer.writeheader()
                writer.writerows(productos)

            return producto

    raise HTTPException(
        status_code=404,
        detail="Producto no encontrado"
    )

# Consultar productos con poco stock
@app.get("/inventory/alerts")
def alertas_inventario(threshold: float = 10):
    if threshold < 0:
        raise HTTPException(
            status_code=400,
            detail="El umbral no puede ser negativo"
        )

    productos = listar_inventario()

    alertas = [
        producto for producto in productos
        if float(producto["quantity"]) < threshold
    ]

    return alertas
  