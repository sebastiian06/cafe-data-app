import pandas as pd


def cargar_csv(archivo):
    """Recibe un archivo CSV subido desde Streamlit y devuelve un DataFrame."""
    if archivo is None:
        raise ValueError("No se recibió ningún archivo.")

    try:
        archivo.seek(0)
        df = pd.read_csv(archivo, encoding="utf-8-sig")
    except UnicodeDecodeError:
        # Si el archivo no está en UTF-8, se intenta con latin-1
        archivo.seek(0)
        df = pd.read_csv(archivo, encoding="latin-1")
    except pd.errors.EmptyDataError:
        raise ValueError("El archivo está vacío.")
    except pd.errors.ParserError:
        raise ValueError("El archivo no tiene un formato CSV válido.")
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo: {e}")

    if df.empty:
        raise ValueError("El archivo no contiene registros.")

    return df