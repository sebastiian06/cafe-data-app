import pandas as pd
import plotly.express as px


def _a_numero(df, columnas):
    """Copia del df con las columnas indicadas convertidas a número (para graficar)."""
    datos = df.copy()
    for columna in columnas:
        datos[columna] = pd.to_numeric(datos[columna], errors="coerce")
    return datos


def _top_productos(df, columna_valor, titulo):
    datos = _a_numero(df, [columna_valor])
    top = (
        datos.groupby("Item", as_index=False)[columna_valor]
        .sum()
        .sort_values(columna_valor, ascending=False)
        .head(10)
    )
    fig = px.bar(top, x=columna_valor, y="Item", orientation="h", title=titulo)
    fig.update_layout(yaxis={"autorange": "reversed"})
    return fig


def _ventas_por(df, columna, titulo, tipo="barras"):
    datos = _a_numero(df, ["Total Spent"])
    agrupado = (
        datos.groupby(columna, as_index=False)["Total Spent"]
        .sum()
        .sort_values("Total Spent", ascending=False)
    )
    if tipo == "pie":
        return px.pie(agrupado, names=columna, values="Total Spent", title=titulo)
    return px.bar(agrupado, x=columna, y="Total Spent", title=titulo)


def top_productos_cantidad(df):
    return _top_productos(df, "Quantity", "Top productos por cantidad vendida")


def top_productos_facturacion(df):
    return _top_productos(df, "Total Spent", "Top productos por facturación")


def ventas_por_ubicacion(df):
    return _ventas_por(df, "Location", "Ventas por ubicación", tipo="pie")


def ventas_por_metodo_pago(df):
    return _ventas_por(df, "Payment Method", "Ventas por método de pago", tipo="pie")


def tendencia_mensual(df):
    datos = _a_numero(df, ["Total Spent"])
    datos["Transaction Date"] = pd.to_datetime(datos["Transaction Date"], errors="coerce")
    datos = datos.dropna(subset=["Transaction Date"])
    datos["mes"] = datos["Transaction Date"].dt.to_period("M").dt.to_timestamp()

    mensual = datos.groupby("mes", as_index=False)["Total Spent"].sum()
    return px.line(
        mensual, x="mes", y="Total Spent", markers=True,
        title="Tendencia mensual de Total Spent",
    )


def scatter_precio_cantidad(df):
    datos = _a_numero(df, ["Price Per Unit", "Quantity"])
    return px.scatter(
        datos, x="Price Per Unit", y="Quantity",
        title="Precio unitario vs cantidad",
    )


def boxplot_total_por_producto(df):
    datos = _a_numero(df, ["Total Spent"])
    return px.box(
        datos, x="Item", y="Total Spent",
        title="Distribución de Total Spent por producto",
    )