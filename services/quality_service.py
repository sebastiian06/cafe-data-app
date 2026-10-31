import pandas as pd

# Textos que en este dataset significan "dato inválido o desconocido"
MARCADORES_INVALIDOS = ["ERROR", "UNKNOWN"]


def perfilar_dataset(df):
    """Analiza el DataFrame y devuelve un resumen. NO modifica los datos."""
    faltantes_por_columna = df.isna().sum()

    perfil = {
        "filas": df.shape[0],
        "columnas": df.shape[1],
        "nombres_columnas": df.columns.tolist(),
        "tipos_datos": df.dtypes.astype(str).to_dict(),
        "faltantes_por_columna": faltantes_por_columna.to_dict(),
        "total_faltantes": int(faltantes_por_columna.sum()),
        "duplicados": int(df.duplicated().sum()),
        "estadisticas": df.describe(),
    }

    return perfil


def _a_numero(df, columna):
    """Convierte una columna a número SOLO para comparar (no cambia el df original)."""
    return pd.to_numeric(df[columna], errors="coerce")


def detectar_problemas(df):
    """Detecta problemas de calidad del dataset de la cafetería. NO corrige ni elimina nada."""
    cantidad = _a_numero(df, "Quantity")
    precio = _a_numero(df, "Price Per Unit")
    total = _a_numero(df, "Total Spent")
    fecha = pd.to_datetime(df["Transaction Date"], format="%Y-%m-%d", errors="coerce")

    # Celdas que contienen ERROR o UNKNOWN (sin importar espacios o mayúsculas)
    es_marcador = df.apply(
        lambda col: col.astype("string").str.strip().str.upper()
        .isin(MARCADORES_INVALIDOS).fillna(False)
    )

    # Regla de consistencia: el total debe ser cantidad x precio
    total_calculado = cantidad * precio
    total_inconsistente = (
        total.notna()
        & total_calculado.notna()
        & ((total - total_calculado).abs() > 0.01)
    )

    # Fecha escrita pero que no se puede convertir a fecha real
    fecha_invalida = df["Transaction Date"].notna() & fecha.isna()

    problemas = {
        "Valores faltantes (celdas vacías)": df[df.isna().any(axis=1)],
        "Valores ERROR / UNKNOWN": df[es_marcador.any(axis=1)],
        "Filas completamente duplicadas": df[df.duplicated()],
        "Transaction ID duplicados": df[df["Transaction ID"].duplicated()],
        "Quantity <= 0": df[cantidad <= 0],
        "Price Per Unit <= 0": df[precio <= 0],
        "Total Spent <= 0": df[total <= 0],
        "Total Spent distinto de Quantity x Price": df[total_inconsistente],
        "Transaction Date no válida": df[fecha_invalida],
    }

    return problemas