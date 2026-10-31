import pandas as pd
from services.quality_service import MARCADORES_INVALIDOS


def eliminar_duplicados(df):
    """Elimina filas completamente duplicadas (conserva la primera aparición)."""
    return df.copy().drop_duplicates()


def reemplazar_marcadores(df, marcadores=MARCADORES_INVALIDOS):
    """Convierte textos como ERROR o UNKNOWN en valores faltantes reales (NaN)."""
    df = df.copy()
    for columna in df.columns:
        texto = df[columna].astype("string").str.strip().str.upper()
        es_marcador = texto.isin(marcadores).fillna(False)
        df[columna] = df[columna].mask(es_marcador)
    return df


def recalcular_montos(df):
    """
    Usa la regla del negocio Total Spent = Quantity x Price Per Unit
    para completar el valor que falta cuando los otros dos existen.
    """
    df = df.copy()
    cantidad = pd.to_numeric(df["Quantity"], errors="coerce")
    precio = pd.to_numeric(df["Price Per Unit"], errors="coerce")
    total = pd.to_numeric(df["Total Spent"], errors="coerce")

    total = total.fillna(cantidad * precio)
    cantidad = cantidad.fillna(total / precio)
    precio = precio.fillna(total / cantidad)

    df["Quantity"] = cantidad
    df["Price Per Unit"] = precio
    df["Total Spent"] = total
    return df


def completar_faltantes(df, columna, estrategia, valor=None):
    """
    Completa valores faltantes de una columna según la estrategia elegida:
    - "media" / "mediana": solo columnas numéricas
    - "moda": el valor más frecuente
    - "valor_fijo": un valor indicado por el usuario
    - "eliminar_filas": quita las filas con faltante en esa columna
    """
    df = df.copy()

    if estrategia == "eliminar_filas":
        return df.dropna(subset=[columna])

    if estrategia in ("media", "mediana"):
        serie = pd.to_numeric(df[columna], errors="coerce")
        relleno = serie.mean() if estrategia == "media" else serie.median()
        df[columna] = serie.fillna(relleno)

    elif estrategia == "moda":
        moda = df[columna].mode()
        if moda.empty:
            raise ValueError(f"La columna '{columna}' no tiene valores para calcular la moda.")
        df[columna] = df[columna].fillna(moda.iloc[0])

    elif estrategia == "valor_fijo":
        if valor is None or valor == "":
            raise ValueError("Debes indicar un valor para completar los faltantes.")
        df[columna] = df[columna].fillna(valor)

    else:
        raise ValueError(f"Estrategia no reconocida: {estrategia}")

    return df


def normalizar_texto(df, columnas):
    """
    Normaliza columnas de texto: quita espacios sobrantes, quita tildes
    y deja un formato uniforme (ej: ' credit card ' -> 'Credit Card').
    """
    df = df.copy()

    for columna in columnas:
        df[columna] = (
            df[columna]
            .astype("string")
            .str.strip()
            .str.lower()
            .str.normalize("NFKD")
            .str.encode("ascii", errors="ignore")
            .str.decode("utf-8")
            .str.replace(r"\s+", " ", regex=True)
            .str.title()
        )

    return df


def eliminar_registros(df, indices):
    """Elimina los registros cuyos índices seleccionó el usuario."""
    return df.copy().drop(index=indices, errors="ignore")


def corregir_valor(df, indice, columna, nuevo_valor):
    """Corrige el valor de una celda específica seleccionada por el usuario."""
    df = df.copy()
    df.loc[indice, columna] = nuevo_valor
    return df


def convertir_tipo(df, columna, tipo):
    """
    Convierte una columna al tipo indicado:
    - "numerico": valores no convertibles quedan como faltantes
    - "fecha": valores no convertibles quedan como faltantes
    - "texto"
    """
    df = df.copy()

    if tipo == "numerico":
        df[columna] = pd.to_numeric(df[columna], errors="coerce")
    elif tipo == "fecha":
        df[columna] = pd.to_datetime(df[columna], errors="coerce")
    elif tipo == "texto":
        df[columna] = df[columna].astype("string")
    else:
        raise ValueError(f"Tipo no reconocido: {tipo}")

    return df