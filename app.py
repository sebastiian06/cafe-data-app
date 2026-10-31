import pandas as pd
import streamlit as st
from services.data_loader import cargar_csv
from services.quality_service import perfilar_dataset, detectar_problemas
from services.cleaning_service import (
    reemplazar_marcadores,
    recalcular_montos,
    eliminar_duplicados,
    completar_faltantes,
    normalizar_texto,
    eliminar_registros,
    corregir_valor,
    convertir_tipo,
)
from services import chart_service


def aplicar_cambio(nuevo_df, mensaje):
    """Guarda el nuevo estado del dataset, registra el cambio y recarga la app."""
    st.session_state.df = nuevo_df
    st.session_state.historial.append(mensaje)
    # Desmarca las confirmaciones para que cada cambio se confirme de nuevo
    for clave in [k for k in st.session_state if str(k).startswith("conf_")]:
        del st.session_state[clave]
    st.rerun()


st.title("Cafe Data Quality")

archivo = st.file_uploader(
    "Carga el CSV de ventas de la cafetería",
    type=["csv"]
)

if not archivo:
    st.stop()

# Cargar el archivo una sola vez y guardarlo en la sesión
id_archivo = f"{archivo.name}-{archivo.size}"
if st.session_state.get("id_archivo") != id_archivo:
    try:
        df_cargado = cargar_csv(archivo)
    except ValueError as e:
        st.error(str(e))
        st.stop()
    st.session_state.df = df_cargado
    st.session_state.id_archivo = id_archivo
    st.session_state.historial = [
        f"Dataset cargado: {archivo.name} ({len(df_cargado)} filas)"
    ]

df = st.session_state.df

st.success("Archivo cargado correctamente")
st.subheader("Primeras 10 filas")
st.dataframe(df.head(10))

# ---------------- Perfil general ----------------
perfil = perfilar_dataset(df)

st.subheader("Perfil general del dataset")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Filas", perfil["filas"])
col2.metric("Columnas", perfil["columnas"])
col3.metric("Valores faltantes", perfil["total_faltantes"])
col4.metric("Duplicados", perfil["duplicados"])

# ---------------- Calidad de datos ----------------
st.header("Calidad de datos")
problemas = detectar_problemas(df)

for nombre, registros in problemas.items():
    cantidad = len(registros)
    with st.expander(f"{nombre} — {cantidad} registros"):
        if cantidad > 0:
            st.dataframe(registros)
        else:
            st.info("No se encontraron registros con este problema.")

# ---------------- Limpieza de datos ----------------
st.header("Limpieza de datos")
st.caption("Ningún cambio se aplica sin tu confirmación. Orden sugerido: de izquierda a derecha.")

tab_marc, tab_calc, tab_dup, tab_falt, tab_norm, tab_tipo, tab_reg = st.tabs(
    ["ERROR / UNKNOWN", "Recalcular montos", "Duplicados", "Faltantes",
     "Normalizar texto", "Tipos de datos", "Registros"]
)

# --- 1. ERROR / UNKNOWN ---
with tab_marc:
    n_marc = len(problemas["Valores ERROR / UNKNOWN"])
    st.write(f"Filas con ERROR o UNKNOWN: **{n_marc}**")
    st.caption("Estos textos se convierten en valores faltantes reales para poder tratarlos.")
    confirmar = st.checkbox("Confirmo reemplazar ERROR/UNKNOWN por vacío", key="conf_marc")
    if st.button("Reemplazar marcadores", disabled=not confirmar or n_marc == 0):
        aplicar_cambio(
            reemplazar_marcadores(df),
            f"Reemplazados ERROR/UNKNOWN por vacío en {n_marc} filas",
        )

# --- 2. Recalcular montos ---
with tab_calc:
    columnas_monto = ["Quantity", "Price Per Unit", "Total Spent"]
    for c in columnas_monto:
        st.write(f"Faltantes en **{c}**: {perfil['faltantes_por_columna'][c]}")
    st.caption("Usa la regla Total Spent = Quantity x Price Per Unit para completar el dato que falta.")
    confirmar = st.checkbox("Confirmo recalcular los montos", key="conf_calc")
    if st.button("Recalcular montos", disabled=not confirmar):
        antes = int(df[columnas_monto].isna().sum().sum())
        nuevo = recalcular_montos(df)
        despues = int(nuevo[columnas_monto].isna().sum().sum())
        aplicar_cambio(nuevo, f"Recalculados montos: {antes - despues} valores recuperados")

# --- 3. Duplicados ---
with tab_dup:
    n_dup = perfil["duplicados"]
    st.write(f"Filas completamente duplicadas: **{n_dup}**")
    confirmar = st.checkbox("Confirmo eliminar las filas duplicadas", key="conf_dup")
    if st.button("Eliminar duplicados", disabled=not confirmar or n_dup == 0):
        aplicar_cambio(eliminar_duplicados(df), f"Eliminados {n_dup} duplicados")

# --- 4. Faltantes ---
with tab_falt:
    cols_faltantes = [c for c, n in perfil["faltantes_por_columna"].items() if n > 0]
    if not cols_faltantes:
        st.info("No hay valores faltantes pendientes.")
    else:
        columna = st.selectbox("Columna con faltantes", cols_faltantes, key="col_falt")
        st.write(f"Faltantes en '{columna}': **{perfil['faltantes_por_columna'][columna]}**")
        estrategia = st.selectbox(
            "Estrategia",
            ["moda", "media", "mediana", "valor_fijo", "eliminar_filas"],
            key="estr_falt",
        )
        valor = None
        if estrategia == "valor_fijo":
            if pd.api.types.is_numeric_dtype(df[columna]):
                valor = st.number_input("Valor para completar", key="valor_falt_num")
            else:
                valor = st.text_input("Valor para completar", key="valor_falt_txt")
        confirmar = st.checkbox("Confirmo completar los faltantes", key="conf_falt")
        if st.button("Aplicar estrategia", disabled=not confirmar):
            try:
                nuevo = completar_faltantes(df, columna, estrategia, valor)
                aplicar_cambio(nuevo, f"Faltantes de '{columna}' tratados con: {estrategia}")
            except ValueError as e:
                st.error(str(e))

# --- 5. Normalizar texto ---
with tab_norm:
    opciones = [c for c in ["Item", "Payment Method", "Location"] if c in df.columns]
    columnas = st.multiselect(
        "Columnas a normalizar", opciones, default=opciones, key="cols_norm"
    )
    for c in columnas:
        st.write(f"**{c}** — valores distintos actuales: {df[c].nunique()}")
    confirmar = st.checkbox("Confirmo normalizar el texto", key="conf_norm")
    if st.button("Normalizar texto", disabled=not confirmar or not columnas):
        aplicar_cambio(
            normalizar_texto(df, columnas),
            f"Normalizadas columnas: {', '.join(columnas)}",
        )

# --- 6. Tipos de datos ---
with tab_tipo:
    columna = st.selectbox("Columna", df.columns.tolist(), key="col_tipo")
    st.write(f"Tipo actual: **{df[columna].dtype}**")
    tipo = st.selectbox("Convertir a", ["numerico", "fecha", "texto"], key="tipo_nuevo")
    if tipo != "texto":
        st.warning("Los valores que no se puedan convertir quedarán como faltantes.")
    confirmar = st.checkbox("Confirmo convertir el tipo de dato", key="conf_tipo")
    if st.button("Convertir tipo", disabled=not confirmar):
        aplicar_cambio(
            convertir_tipo(df, columna, tipo),
            f"Columna '{columna}' convertida a {tipo}",
        )

# --- 7. Registros (eliminar o corregir) ---
with tab_reg:
    con_casos = [n for n, r in problemas.items() if len(r) > 0]
    if not con_casos:
        st.info("No hay registros con problemas pendientes.")
    else:
        problema = st.selectbox("Problema a revisar", con_casos, key="prob_reg")
        registros = problemas[problema]
        st.dataframe(registros)

        accion = st.radio(
            "Acción", ["Eliminar registros", "Corregir un valor"],
            key="accion_reg", horizontal=True,
        )

        if accion == "Eliminar registros":
            indices = st.multiselect(
                "Índices de los registros a eliminar",
                registros.index.tolist(), key="idx_elim",
            )
            confirmar = st.checkbox("Confirmo eliminar los registros seleccionados", key="conf_elim")
            if st.button("Eliminar registros", disabled=not confirmar or not indices):
                aplicar_cambio(
                    eliminar_registros(df, indices),
                    f"Eliminados {len(indices)} registros ({problema}): índices {indices}",
                )
        else:
            indice = st.selectbox("Índice del registro", registros.index.tolist(), key="idx_corr")
            columna = st.selectbox("Columna a corregir", df.columns.tolist(), key="col_corr")
            valor_actual = df.loc[indice, columna]
            st.write(f"Valor actual: **{valor_actual}**")

            if pd.api.types.is_integer_dtype(df[columna]):
                nuevo_valor = st.number_input("Nuevo valor", step=1, value=0, key="nuevo_int")
            elif pd.api.types.is_numeric_dtype(df[columna]):
                nuevo_valor = st.number_input("Nuevo valor", key="nuevo_num")
            else:
                nuevo_valor = st.text_input("Nuevo valor", key="nuevo_txt")

            confirmar = st.checkbox("Confirmo corregir este valor", key="conf_corr")
            if st.button("Corregir valor", disabled=not confirmar):
                aplicar_cambio(
                    corregir_valor(df, indice, columna, nuevo_valor),
                    f"Corregido '{columna}' en índice {indice}: {valor_actual} -> {nuevo_valor}",
                )

# ---------------- Historial ----------------
st.header("Historial de transformaciones")
for i, paso in enumerate(st.session_state.historial, start=1):
    st.write(f"{i}. {paso}")

# ---------------- Visualizaciones ----------------
st.header("Visualizaciones")

graficos = [
    ("Top productos por cantidad", chart_service.top_productos_cantidad),
    ("Top productos por facturación", chart_service.top_productos_facturacion),
    ("Ventas por ubicación", chart_service.ventas_por_ubicacion),
    ("Ventas por método de pago", chart_service.ventas_por_metodo_pago),
    ("Tendencia mensual", chart_service.tendencia_mensual),
    ("Precio unitario vs cantidad", chart_service.scatter_precio_cantidad),
    ("Boxplot por producto", chart_service.boxplot_total_por_producto),
]

for titulo, funcion in graficos:
    try:
        st.plotly_chart(funcion(df), width="stretch")
    except (KeyError, ValueError) as e:
        st.warning(f"No se pudo generar '{titulo}': {e}")

# ---------------- Exportar ----------------
st.header("Exportar")

reglas_negocio = {
    nombre: registros
    for nombre, registros in problemas.items()
    if nombre not in ("Valores faltantes (celdas vacías)", "Filas completamente duplicadas")
}
pendientes_reglas = sum(len(r) for r in reglas_negocio.values())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Filas finales", perfil["filas"])
c2.metric("Columnas finales", perfil["columnas"])
c3.metric("Faltantes pendientes", perfil["total_faltantes"])
c4.metric("Duplicados pendientes", perfil["duplicados"])
c5.metric("Reglas de negocio pendientes", pendientes_reglas)

csv = df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Descargar dataset limpio",
    data=csv,
    file_name="dataset_cafe_limpio.csv",
    mime="text/csv",
)