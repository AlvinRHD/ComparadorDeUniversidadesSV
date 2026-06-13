"""
PROYECTO FINAL - Comparador de Universidades El Salvador
Archivo: dashboard.py
Ejecutar: streamlit run dashboard.py
"""

import os, json, io
import pandas as pd
import streamlit as st
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import folium
from streamlit_folium import st_folium
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime

# --------------------------------═══
#  MAPEO DE REQUISITOS - dashboard.py
# --------------------------------═══
#  ALMACENAMIENTO (obligatorio):
#     OK DataFrame de pandas -> sección "DATAFRAMES" (df_resumen, df_detalle)
#
#  MINERÍA DE DATOS (obligatorio) -> TAB 2 "Minería de Datos"
#     OK Palabras más frecuentes  -> tabla "freq" + gráfica Top 10
#     OK Categorías predominantes -> dataframe "predominantes"
#     OK Tendencias encontradas   -> fig_tend (universidades con más presencia académica)
#     OK Frecuencias              -> freq, heatmap "pivot"
#     (Precio prom/min/max no aplica: el proyecto es académico, no de precios)
#
#  VISUALIZACIÓN (obligatorio, mínimo 3 -> aquí hay 4+):
#     OK Gráfica de barras -> TAB 1 (fig, fig3) y TAB 2 (fig_top, fig_tend)
#     OK Histograma        -> TAB 1 (fig2 - páginas visitadas)
#     OK Tabla de resultados -> TAB 1 (st.dataframe df_resumen) y TAB 2 (df_f)
#     OK Dashboard web     -> todo el archivo (streamlit run dashboard.py)
#
# alert MANEJO DE ERRORES (obligatorio):
#     OK Datos vacíos -> chequeos "if not os.path.exists", "if not archivos",
#        "if df_detalle.empty" antes de graficar
#
# start EXTRAS (opcionales, puntos adicionales):
#     OK Nube de palabras       -> TAB 3
#     OK Geolocalización (mapa) -> TAB 4 (folium + streamlit_folium)
#     OK Comparación entre sitios -> TAB 5 (compara 2 universidades)
#     OK Exportación a PDF      -> TAB 6 (reportlab)
#     ERROR Análisis de sentimientos -> NO implementado todavía
# --------------------------------═══

# ----------------------─
# CONFIGURACIÓN
# ----------------------─

st.set_page_config(page_title="Universidades El Salvador", page_icon="", layout="wide")
st.title(" Comparador de Universidades - El Salvador")
st.caption("Web Scraping + Minería de Datos | Proyecto Final BD")

CARPETA_RESULTADOS = "resultados"

if not os.path.exists(CARPETA_RESULTADOS):
    # alert REQUISITO: manejo de errores -> datos vacíos (carpeta de resultados inexistente)
    st.error("No existe 'resultados/'. Ejecutá primero crawler.py"); st.stop()

archivos = sorted([f for f in os.listdir(CARPETA_RESULTADOS) if f.endswith(".json")], reverse=True)
if not archivos:
    # alert REQUISITO: manejo de errores -> datos vacíos (sin archivos JSON)
    st.error("No hay archivos JSON. Ejecutá primero crawler.py"); st.stop()

# ----------------------─
# SIDEBAR
# ----------------------─

st.sidebar.header("Datos")
archivo_sel = st.sidebar.selectbox("Seleccioná un resultado:", archivos, index=0)
st.sidebar.caption(f"`{archivo_sel}`")

# ---------──
#  BOTÓN EJECUTAR CRAWLER (sidebar)
# Se agrega aquí porque el sidebar ya muestra los JSON disponibles,
# y el botón queda naturalmente "debajo de los resultados".
# ---------──
import subprocess  # ← Agregar este import arriba junto a los demás imports del archivo

st.sidebar.divider()
st.sidebar.markdown("### Actualizar datos")

if st.sidebar.button("Ejecutar crawler.py", use_container_width=True):
    # Contenedor donde irán apareciendo los mensajes de progreso en vivo
    log_box = st.sidebar.empty()

    try:
        # subprocess.Popen ejecuta crawler.py como proceso aparte.
        # stdout=PIPE captura lo que normalmente saldría en consola.
        # stderr=STDOUT mezcla errores en el mismo canal para no perderlos.
        # text=True hace que las líneas lleguen como string (no bytes).
        proceso = subprocess.Popen(
            ["python", "crawler.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"        # evita crash si hay carácter raro
        )

        log_acumulado = ""          # guardamos todo el log para mostrarlo completo

        # Leemos línea a línea MIENTRAS el proceso sigue corriendo.
        # Esto da el efecto "streaming" que permite ver el progreso en tiempo real.
        for linea in proceso.stdout:
            linea = linea.rstrip()
            if not linea:
                continue            # ignoramos líneas vacías

            # Detectamos las líneas que mencionan universidades para mostrarlas bonito
            if "[" in linea and "]" in linea:
                log_acumulado += f"OK {linea}\n"
            else:
                log_acumulado += f"{linea}\n"

            # Actualizamos el mismo cuadro de texto en lugar de agregar líneas nuevas
            log_box.text_area(
                "Log del crawler:",
                value=log_acumulado,
                height=300
                # sin key -> Streamlit lo maneja solo porque usamos .empty()
            )

        proceso.wait()              # esperamos a que termine formalmente

        # Mensaje final según el código de salida (0 = éxito, otro = error)
        if proceso.returncode == 0:
            st.sidebar.success("OK ¡Crawler finalizado! Recargá la página para ver los datos actualizados.")
        else:
            st.sidebar.error(f"ERROR El crawler terminó con errores (código {proceso.returncode}).")

    except FileNotFoundError:
        # alert Manejo de errores: crawler.py no existe en la carpeta actual
        st.sidebar.error("ERROR No se encontró crawler.py. Asegurate de que esté en la misma carpeta.")
    except Exception as e:
        # alert Manejo de errores: cualquier fallo inesperado al lanzar el proceso
        st.sidebar.error(f"ERROR Error al ejecutar el crawler: {e}")

with open(os.path.join(CARPETA_RESULTADOS, archivo_sel), "r", encoding="utf-8") as f:
    datos = json.load(f)

# ----------------------─
#  DATAFRAMES (REQUISITO: almacenamiento en pandas)
# ----------------------─

resumen = []
for siglas, d in datos.items():
    resumen.append({
        "Siglas":            siglas,
        "Universidad":       d["nombre"],
        "Páginas visitadas": d["paginas_visitadas"],
        "Coincidencias":     d["coincidencias"],
        "Correos":           len(d.get("correos", [])),
        "Teléfonos":         len(d.get("telefonos", [])),
        "Lat":               d.get("lat", 0),
        "Lng":               d.get("lng", 0),
    })
df_resumen = pd.DataFrame(resumen)

detalle = []
for siglas, d in datos.items():
    for r in d["resultados"]:
        detalle.append({
            "Universidad": siglas,
            "Palabra":     r["palabra"],
            "Título":      r["titulo"],
            "URL":         r["url"]
        })
df_detalle = pd.DataFrame(detalle)

# ----------------------─
# MÉTRICAS SUPERIORES
# ----------------------─

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Universidades",     len(datos))
c2.metric("Páginas visitadas", int(df_resumen["Páginas visitadas"].sum()))
c3.metric("Coincidencias",     int(df_resumen["Coincidencias"].sum()))
c4.metric("Correos hallados",  int(df_resumen["Correos"].sum()))
c5.metric("Teléfonos hallados",int(df_resumen["Teléfonos"].sum()))

st.divider()

# ----------------------─
# PESTAÑAS
# ----------------------─

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    " Resumen", " Minería de Datos", " Nube de palabras",
    "Mapa", " Comparación", " Acerca de", "Archivos", "Buscador..."
])

# --------------------------------
# TAB 1 - RESUMEN
# --------------------------------

with tab1:
    # Tabla de resultados (requisito visualización)
    st.subheader(" Tabla de resultados - DataFrame principal")
    st.caption("Datos almacenados en pandas DataFrame y visualizados aquí")
    st.dataframe(
        df_resumen[["Siglas","Universidad","Páginas visitadas","Coincidencias","Correos","Teléfonos"]],
        width="stretch", hide_index=True
    )
    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        # Gráfica de barras - coincidencias (requisito)
        fig = px.bar(df_resumen, x="Siglas", y="Coincidencias", color="Siglas",
                     text="Coincidencias",
                     title=" Gráfica de barras - Palabras clave por universidad",
                     labels={"Coincidencias": "Palabras clave encontradas"})
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, xaxis_title="Universidad", yaxis_title="Cantidad")
        st.plotly_chart(fig, width="stretch")

    with col_b:
        # Histograma - páginas visitadas (requisito)
        fig2 = px.histogram(df_resumen, x="Páginas visitadas", nbins=5,
                            title=" Histograma - Distribución de páginas visitadas",
                            labels={"Páginas visitadas": "Páginas visitadas", "count": "Frecuencia"},
                            color_discrete_sequence=["#3b82f6"])
        fig2.update_layout(xaxis_title="Páginas visitadas", yaxis_title="Frecuencia")
        st.plotly_chart(fig2, width="stretch")

    # Gráfica agrupada contactos
    df_m = df_resumen.melt(id_vars="Siglas", value_vars=["Correos","Teléfonos"],
                            var_name="Tipo", value_name="Cantidad")
    fig3 = px.bar(df_m, x="Siglas", y="Cantidad", color="Tipo", barmode="group",
                  title=" Correos y teléfonos encontrados por universidad",
                  labels={"Cantidad": "Cantidad encontrada", "Siglas": "Universidad"})
    fig3.update_layout(xaxis_title="Universidad", yaxis_title="Cantidad")
    st.plotly_chart(fig3, width="stretch")


# --------------------------------
# TAB 2 - MINERÍA DE DATOS
# --------------------------------

with tab2:
    st.subheader(" Minería de Datos - Análisis académico")

    if df_detalle.empty:
        # alert REQUISITO: manejo de errores -> datos vacíos
        st.warning("No hay datos.")
    else:
        # - Análisis de frecuencias -
        freq = df_detalle.groupby("Palabra").size().reset_index(name="Frecuencia").sort_values("Frecuencia", ascending=False)

        # Estadísticas tipo minería (máximo, mínimo, promedio, tendencia)
        st.markdown("#### 🔢 Estadísticas de frecuencia de términos académicos")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(" Término más frecuente",  f"{freq.iloc[0]['Palabra']} ({freq.iloc[0]['Frecuencia']})")
        m2.metric(" Término menos frecuente", f"{freq.iloc[-1]['Palabra']} ({freq.iloc[-1]['Frecuencia']})")
        m3.metric(" Frecuencia promedio",     f"{freq['Frecuencia'].mean():.1f}")
        m4.metric(" Total términos únicos",   len(freq))

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            # Top 10 palabras
            fig_top = px.bar(freq.head(10), x="Frecuencia", y="Palabra", orientation="h",
                             title=" Top 10 - Términos académicos más frecuentes",
                             labels={"Frecuencia": "Veces encontrado", "Palabra": "Término"},
                             color="Frecuencia", color_continuous_scale="Blues")
            fig_top.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False)
            st.plotly_chart(fig_top, width="stretch")

        with col_b:
            # Categorías predominantes por universidad
            st.markdown("####  Categoría predominante por universidad")
            predominantes = (
                df_detalle.groupby(["Universidad","Palabra"]).size()
                .reset_index(name="Frecuencia")
                .sort_values("Frecuencia", ascending=False)
                .groupby("Universidad").first().reset_index()
                [["Universidad","Palabra","Frecuencia"]]
            )
            st.dataframe(predominantes, width="stretch", hide_index=True)

            st.markdown("####  Tendencia - Universidades con más presencia académica")
            fig_tend = px.bar(
                df_resumen.sort_values("Coincidencias", ascending=False),
                x="Siglas", y="Coincidencias",
                title="Tendencia de presencia académica en la web",
                color="Coincidencias", color_continuous_scale="Blues",
                labels={"Coincidencias": "Términos académicos detectados", "Siglas": "Universidad"}
            )
            fig_tend.update_layout(showlegend=False)
            st.plotly_chart(fig_tend, width="stretch")

        st.divider()

        # Heatmap distribución
        pivot = df_detalle.groupby(["Universidad","Palabra"]).size().reset_index(name="Frecuencia")
        fig_heat = px.density_heatmap(pivot, x="Universidad", y="Palabra", z="Frecuencia",
                                       color_continuous_scale="Blues",
                                       title=" Distribución de términos académicos por universidad")
        fig_heat.update_layout(xaxis_title="Universidad", yaxis_title="Término académico")
        st.plotly_chart(fig_heat, width="stretch")

        st.divider()

        # DataFrame completo con filtro
        st.markdown("#### 🔎 Explorar datos - filtro por universidad")
        uni_sel = st.selectbox("Universidad:", ["Todas"] + list(datos.keys()), key="filtro_mineria")
        df_f = df_detalle if uni_sel == "Todas" else df_detalle[df_detalle["Universidad"] == uni_sel]
        st.dataframe(df_f[["Universidad","Palabra","Título","URL"]].drop_duplicates(),
                     width="stretch", hide_index=True)


# --------------------------------
# TAB 3 - NUBE DE PALABRAS
# --------------------------------

with tab3:
    # start REQUISITO EXTRA: Nube de palabras
    st.subheader(" Nube de palabras")

    if df_detalle.empty:
        # alert REQUISITO: manejo de errores -> datos vacíos
        st.warning("No hay palabras para generar la nube.")
    else:
        uni_nube = st.selectbox("Generar nube para:", ["Todas"] + list(datos.keys()), key="nube")
        df_nube  = df_detalle if uni_nube == "Todas" else df_detalle[df_detalle["Universidad"] == uni_nube]
        freq_nube = df_nube.groupby("Palabra").size().to_dict()

        if freq_nube:
            wc = WordCloud(
                width=1400, height=600,
                background_color=None,   # fondo transparente
                mode="RGBA",
                colormap="Blues",
                max_words=80,
                prefer_horizontal=0.7,
                min_font_size=14,
                max_font_size=120,
                relative_scaling=0.6,
                collocations=False
            ).generate_from_frequencies(freq_nube)

            fig_wc, ax = plt.subplots(figsize=(14, 6))
            fig_wc.patch.set_alpha(0)          # figura transparente
            ax.set_facecolor("none")           # axes transparente
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            plt.tight_layout(pad=0)
            st.pyplot(fig_wc, use_container_width=True)
        else:
            st.info("No hay palabras para esta selección.")


# --------------------------------
# TAB 4 - MAPA
# --------------------------------

with tab4:
    # start REQUISITO EXTRA: Geolocalización
    st.subheader(" Ubicación de universidades en El Salvador")

    mapa = folium.Map(location=[13.7942, -88.8965], zoom_start=8, tiles="CartoDB positron")

    for _, row in df_resumen.iterrows():
        if row["Lat"] and row["Lng"]:
            folium.CircleMarker(
                location=[row["Lat"], row["Lng"]],
                radius=10,
                color="#1d4ed8",
                fill=True, fill_color="#3b82f6", fill_opacity=0.85,
                tooltip=f"{row['Siglas']} - {row['Universidad']}",
                popup=folium.Popup(
                    f"<b>{row['Universidad']}</b><br>"
                    f"Páginas visitadas: {row['Páginas visitadas']}<br>"
                    f"Coincidencias: {row['Coincidencias']}<br>"
                    f"Correos: {row['Correos']}<br>"
                    f"Teléfonos: {row['Teléfonos']}",
                    max_width=230
                )
            ).add_to(mapa)

    st_folium(mapa, width="100%", height=520)
    st.caption("Hacé clic en cada punto para ver el detalle.")


# --------------------------------
# TAB 5 - COMPARACIÓN
# --------------------------------

with tab5:
    # start REQUISITO EXTRA: Comparación entre sitios web (universidades)
    st.subheader("🔍 Comparar dos universidades")
    unis = list(datos.keys())

    if len(unis) < 2:
        st.warning("Necesitás al menos 2 universidades.")
    else:
        ca, cb = st.columns(2)
        uni_a = ca.selectbox("Universidad A:", unis, index=0, key="comp_a")
        uni_b = cb.selectbox("Universidad B:", unis, index=min(1, len(unis)-1), key="comp_b")

        if uni_a == uni_b:
            st.warning("Seleccioná dos universidades distintas.")
        else:
            da, db = datos[uni_a], datos[uni_b]
            palabras_a = set(r["palabra"] for r in da["resultados"])
            palabras_b = set(r["palabra"] for r in db["resultados"])

            col1, col2 = st.columns(2)
            for col, siglas, d, palabras in [(col1, uni_a, da, palabras_a), (col2, uni_b, db, palabras_b)]:
                with col:
                    st.markdown(f"### {siglas} - {d['nombre']}")
                    st.metric("Páginas visitadas", d["paginas_visitadas"])
                    st.metric("Coincidencias",     d["coincidencias"])
                    st.metric("Correos",           len(d.get("correos",[])))
                    st.metric("Teléfonos",         len(d.get("telefonos",[])))
                    st.markdown(f"**Términos:** {', '.join(sorted(palabras))}")

            st.divider()

            # Palabras en común y exclusivas
            comunes = palabras_a & palabras_b
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"** En común**\n\n{', '.join(sorted(comunes)) or 'Ninguna'}")
            c2.markdown(f"**Solo {uni_a}**\n\n{', '.join(sorted(palabras_a - palabras_b)) or 'Ninguna'}")
            c3.markdown(f"**Solo {uni_b}**\n\n{', '.join(sorted(palabras_b - palabras_a)) or 'Ninguna'}")

            st.divider()

            # Gráfica comparativa
            df_comp = pd.DataFrame([
                {"Métrica": "Páginas visitadas", uni_a: da["paginas_visitadas"],    uni_b: db["paginas_visitadas"]},
                {"Métrica": "Coincidencias",     uni_a: da["coincidencias"],        uni_b: db["coincidencias"]},
                {"Métrica": "Correos",           uni_a: len(da.get("correos",[])),  uni_b: len(db.get("correos",[]))},
                {"Métrica": "Teléfonos",         uni_a: len(da.get("telefonos",[])),uni_b: len(db.get("telefonos",[]))},
            ]).melt(id_vars="Métrica", var_name="Universidad", value_name="Valor")

            fig_comp = px.bar(df_comp, x="Métrica", y="Valor", color="Universidad",
                              barmode="group", title=f"Comparación: {uni_a} vs {uni_b}",
                              labels={"Valor": "Cantidad", "Métrica": "Indicador"})
            st.plotly_chart(fig_comp, width="stretch")


# --------------------------------
# TAB 6 - ACERCA DE + EXPORTAR PDF
# --------------------------------

with tab6:
    st.subheader(" Acerca del proyecto")
    st.markdown("""
    **Proyecto Final - Bases de Datos**  
    Universidad de Oriente (UNIVO) · El Salvador · 2026

    Sistema de **web crawling y scraping** sobre los sitios oficiales de las universidades
    de El Salvador para extraer, almacenar y comparar información académica.

    | Componente | Descripción |
    |---|---|
    | 🕷️ Crawler | Recorre páginas internas respetando el dominio |
    |  Scraping | Extrae palabras clave, correos, teléfonos e imágenes |
    |  Almacenamiento | pandas DataFrame + MySQL (universidades_sv) |
    |  Minería | Frecuencias, tendencias y categorías predominantes |
    |  Visualización | Barras, histograma, heatmap, nube, mapa |
    |  Interfaz | Dashboard web con Streamlit |

    **Tecnologías:** `requests` · `BeautifulSoup` · `pandas` · `plotly` · `wordcloud` · `folium` · `MySQL` · `streamlit`

    **Flujo:**
    ```
    python crawler.py  ->  resultados/  imagenes_descargadas/  contactos/  MySQL
    streamlit run dashboard.py
    ```
    """)

    st.divider()
    # start REQUISITO EXTRA: Exportación a PDF
    st.subheader(" Exportar reporte PDF")

    if st.button("Generar PDF"):
        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=letter,
                                   leftMargin=0.75*inch, rightMargin=0.75*inch,
                                   topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()
        azul   = colors.HexColor("#1d4ed8")
        gris   = colors.HexColor("#f1f5f9")

        titulo_style = ParagraphStyle("titulo", parent=styles["Title"],
                                      textColor=azul, fontSize=18, spaceAfter=4)
        sub_style    = ParagraphStyle("sub", parent=styles["Heading2"],
                                      textColor=azul, fontSize=12, spaceBefore=12, spaceAfter=4)
        normal       = styles["Normal"]

        story = []

        # Encabezado
        story.append(Paragraph("Reporte de Universidades - El Salvador", titulo_style))
        story.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Archivo: {archivo_sel}", normal))
        story.append(HRFlowable(width="100%", thickness=1.5, color=azul, spaceAfter=10))

        # Resumen numérico
        story.append(Paragraph("Resumen general", sub_style))
        datos_resumen = [
            ["Universidades analizadas", str(len(datos))],
            ["Total páginas visitadas",  str(int(df_resumen["Páginas visitadas"].sum()))],
            ["Total coincidencias",      str(int(df_resumen["Coincidencias"].sum()))],
            ["Total correos hallados",   str(int(df_resumen["Correos"].sum()))],
            ["Total teléfonos hallados", str(int(df_resumen["Teléfonos"].sum()))],
        ]
        t_res = Table(datos_resumen, colWidths=[3.5*inch, 2*inch])
        t_res.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (0,-1), gris),
            ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, gris]),
            ("ALIGN",       (1,0), (1,-1), "CENTER"),
        ]))
        story.append(t_res)

        # Tabla principal
        story.append(Spacer(1, 10))
        story.append(Paragraph("Detalle por universidad", sub_style))
        encabezado = [["Siglas","Universidad","Páginas","Coincidencias","Correos","Teléfonos"]]
        filas = encabezado + [
            [row["Siglas"], row["Universidad"], str(row["Páginas visitadas"]),
             str(row["Coincidencias"]), str(row["Correos"]), str(row["Teléfonos"])]
            for _, row in df_resumen.iterrows()
        ]
        t_main = Table(filas, colWidths=[0.7*inch, 2.8*inch, 0.8*inch, 1.1*inch, 0.8*inch, 0.8*inch])
        t_main.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0), azul),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, gris]),
            ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
            ("ALIGN",       (2,0), (-1,-1), "CENTER"),
        ]))
        story.append(t_main)

        # Top palabras
        story.append(Spacer(1, 10))
        story.append(Paragraph("Minería de datos - Top 10 términos académicos", sub_style))
        if not df_detalle.empty:
            top = (df_detalle.groupby("Palabra").size()
                   .reset_index(name="Frecuencia")
                   .sort_values("Frecuencia", ascending=False).head(10))
            t_pal = Table(
                [["Término", "Frecuencia"]] + [[r["Palabra"], str(r["Frecuencia"])] for _, r in top.iterrows()],
                colWidths=[3*inch, 1.5*inch]
            )
            t_pal.setStyle(TableStyle([
                ("BACKGROUND",  (0,0), (-1,0), azul),
                ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
                ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",    (0,0), (-1,-1), 9),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, gris]),
                ("GRID",        (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
                ("ALIGN",       (1,0), (1,-1), "CENTER"),
            ]))
            story.append(t_pal)

        # Pie
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1")))
        story.append(Paragraph("Proyecto Final BD - UNIVO 2026", normal))

        doc.build(story)
        buffer.seek(0)

        st.download_button(" Descargar PDF", data=buffer,
                           file_name="reporte_universidades.pdf", mime="application/pdf")
        
# --------------------------------
# TAB 7 - IMÁGENES, CORREOS Y TELÉFONOS
# --------------------------------

with tab7:
    st.subheader("Archivos descargados por universidad")

    CARPETA_IMAGENES  = "imagenes_descargadas"
    CARPETA_CONTACTOS = "contactos"

    # Selector de universidad - usamos las siglas del JSON activo
    unis_disponibles = list(datos.keys())
    uni_arch = st.selectbox(
        "Seleccioná una universidad:",
        unis_disponibles,
        format_func=lambda s: f"{s} - {datos[s]['nombre']}",
        key="sel_archivos"
    )

    st.divider()

    # ── SECCIÓN 1: CONTACTOS ----------──

    ruta_contacto = os.path.join(CARPETA_CONTACTOS, f"{uni_arch}_contactos.json")

    col_correos, col_telefonos = st.columns(2)

    with col_correos:
        st.markdown("#### Correos electrónicos")
        # Intentamos leer del archivo de contactos; fallback al JSON de resultados
        if os.path.exists(ruta_contacto):
            with open(ruta_contacto, "r", encoding="utf-8") as f:
                contactos = json.load(f)
            correos = contactos.get("correos", [])
        else:
            #  Manejo de errores: archivo no existe, usamos los datos del JSON principal
            correos = datos[uni_arch].get("correos", [])

        if correos:
            for c in correos:
                # Mostramos cada correo como badge/chip limpio
                st.markdown(
                    f'<span style="background:#eff6ff;color:#1d4ed8;padding:4px 10px;'
                    f'border-radius:20px;font-size:0.85rem;display:inline-block;margin:3px">'
                    f'✉️ {c}</span>',
                    unsafe_allow_html=True
                )
        else:
            st.caption("Sin correos registrados.")

    with col_telefonos:
        st.markdown("#### Teléfonos")
        if os.path.exists(ruta_contacto):
            telefonos = contactos.get("telefonos", [])
        else:
            telefonos = datos[uni_arch].get("telefonos", [])

        if telefonos:
            for t in telefonos:
                st.markdown(
                    f'<span style="background:#f0fdf4;color:#15803d;padding:4px 10px;'
                    f'border-radius:20px;font-size:0.85rem;display:inline-block;margin:3px">'
                    f' {t}</span>',
                    unsafe_allow_html=True
                )
        else:
            st.caption("Sin teléfonos registrados.")

    st.divider()

    # ── SECCIÓN 2: IMÁGENES -----------

    st.markdown("#### 🖼️ Imágenes descargadas")

    carpeta_imgs = os.path.join(CARPETA_IMAGENES, uni_arch)

    if not os.path.exists(carpeta_imgs):
        # Manejo de errores: carpeta de imágenes no existe
        st.caption("No hay imágenes descargadas para esta universidad.")
    else:
        # Filtramos solo extensiones de imagen válidas
        EXTS_VALIDAS = {".jpg", ".jpeg", ".png", ".webp"}
        imagenes = [
            f for f in os.listdir(carpeta_imgs)
            if os.path.splitext(f)[1].lower() in EXTS_VALIDAS
        ]

        if not imagenes:
            st.caption("La carpeta existe pero no tiene imágenes.")
        else:
            st.caption(f"{len(imagenes)} imagen(es) encontrada(s) en `{carpeta_imgs}/`")

            # Mostramos en grilla de 4 columnas para que se vea compacto y ordenado
            COLS = 4
            for i in range(0, len(imagenes), COLS):
                fila = imagenes[i:i + COLS]
                cols = st.columns(COLS)
                for col, nombre_img in zip(cols, fila):
                    ruta_img = os.path.join(carpeta_imgs, nombre_img)
                    with col:
                        try:
                            # st.image maneja PNG/JPG/WEBP nativamente
                            st.image(ruta_img, caption=nombre_img, use_container_width=True)
                        except Exception:
                            #  Manejo de errores: imagen corrupta o ilegible
                            st.caption(f" {nombre_img} no se pudo mostrar")


# --------------------------------
# TAB 8 - BUSCADOR
# Permite buscar términos académicos o nombres de carrera
# y muestra resultados estilo Google: título + universidad + URL clickeable
# --------------------------------

with tab8:
    st.subheader("Buscador de carreras y términos académicos")
    st.caption("Buscá una carrera, término o palabra clave y encontrá qué universidades la mencionan en su sitio web.")

    # ── Lista de palabras clave del crawler (mismas que en crawler.py)
    # Se usan como filtros rápidos para que el usuario no tenga que escribir
    PALABRAS_FILTRO = [
        "carrera", "ingeniería", "facultad", "maestría",
        "técnico", "licenciatura", "pregrado", "posgrado",
        "administración", "derecho", "medicina",
        "arquitectura", "computación"
    ]

    # ── FILA SUPERIOR: barra de búsqueda + filtros rápidos ---──
    col_search, col_filtro = st.columns([3, 2])

    with col_search:
        # Campo de texto principal - el usuario escribe lo que busca
        query = st.text_input(
            "Buscar:",
            placeholder="Ej: ingeniería, medicina, maestría en negocios...",
            label_visibility="collapsed"
        )

    with col_filtro:
        # Chips de filtro rápido: al seleccionar uno, se usa como búsqueda
        # Si el usuario también escribió algo en el text_input, el chip lo sobreescribe
        filtro_rapido = st.selectbox(
            "O elegí un término:",
            ["- Seleccioná un filtro -"] + PALABRAS_FILTRO,
            label_visibility="collapsed"
        )

    # Determinamos el término final a buscar:
    # prioridad -> lo que escribió el usuario; si está vacío, usamos el filtro
    termino = query.strip()
    if not termino and filtro_rapido != "- Seleccioná un filtro -":
        termino = filtro_rapido

    st.divider()

    # ── LÓGICA DE BÚSQUEDA ------------
    if not termino:
        # Estado inicial: no se buscó nada todavía
        st.info("Escribí algo en la barra o elegí un filtro rápido para empezar.")

    else:
        termino_lower = termino.lower()

        # Recorremos el JSON completo buscando coincidencias en:
        # 1) el campo "palabra" de cada resultado  (término académico detectado)
        # 2) el campo "titulo" de la página        (título HTML de la página)
        # Así si alguien busca "medicina" encuentra páginas aunque el término
        # no sea exactamente una de las PALABRAS_CLAVE del crawler
        resultados_busqueda = []

        for siglas, d in datos.items():
            nombre_uni = d["nombre"]
            url_base   = next(
                # Tomamos la URL del primer resultado como "URL principal" de la uni
                (r["url"] for r in d["resultados"] if r["url"]),
                "#"
            )

            for r in d["resultados"]:
                # Revisamos si el término aparece en la palabra clave o en el título
                palabra_ok = termino_lower in r["palabra"].lower()
                titulo_ok  = termino_lower in r["titulo"].lower()

                if palabra_ok or titulo_ok:
                    resultados_busqueda.append({
                        "siglas":      siglas,
                        "universidad": nombre_uni,
                        "palabra":     r["palabra"],
                        "titulo":      r["titulo"],
                        "url":         r["url"],
                        "url_base":    url_base,
                    })

        # Eliminamos duplicados exactos (misma url + misma palabra)
        vistos = set()
        unicos = []
        for res in resultados_busqueda:
            llave = (res["url"], res["palabra"])
            if llave not in vistos:
                vistos.add(llave)
                unicos.append(res)

        # ── ENCABEZADO DE RESULTADOS (estilo Google) -----──
        if not unicos:
            # Manejo de errores: búsqueda sin resultados
            st.warning(f"No se encontraron resultados para **\"{termino}\"**. "
                       f"Intentá con otro término o ejecutá el crawler para actualizar los datos.")
        else:
            # Agrupamos por universidad para saber cuántas encontraron el término
            unis_con_resultados = len(set(r["siglas"] for r in unicos))
            st.success(f"**{len(unicos)} resultado(s)** en **{unis_con_resultados} universidad(es)** "
                       f"para «{termino}»")

            st.markdown("")  # pequeño espacio visual

            # ── TARJETAS DE RESULTADO (una por coincidencia) ---──
            for res in unicos:
                # Contenedor con borde suave - simula tarjeta de resultado de búsqueda
                with st.container(border=True):
                    col_info, col_link = st.columns([5, 1])

                    with col_info:
                        # Línea 1: nombre de la universidad (como el "sitio" en Google)
                        st.markdown(
                            f'<span style="color:#6b7280;font-size:0.82rem;">'
                            f'{res["universidad"]} &nbsp;·&nbsp; '
                            f'<code style="background:#f1f5f9;padding:1px 6px;border-radius:4px;">'
                            f'{res["siglas"]}</code></span>',
                            unsafe_allow_html=True
                        )

                        # Línea 2: título de la página (como el título azul clickeable en Google)
                        titulo_mostrar = res["titulo"] if res["titulo"] else "Sin título"
                        st.markdown(
                            f'<a href="{res["url"]}" target="_blank" '
                            f'style="font-size:1.05rem;font-weight:600;color:#1d4ed8;'
                            f'text-decoration:none;">{titulo_mostrar}</a>',
                            unsafe_allow_html=True
                        )

                        # Línea 3: URL visible (como la URL verde en Google)
                        st.markdown(
                            f'<span style="color:#16a34a;font-size:0.78rem;">{res["url"]}</span>',
                            unsafe_allow_html=True
                        )

                        # Línea 4: etiqueta de término académico detectado
                        st.markdown(
                            f'<span style="background:#eff6ff;color:#1e40af;padding:2px 8px;'
                            f'border-radius:12px;font-size:0.78rem;"> {res["palabra"]}</span>',
                            unsafe_allow_html=True
                        )

                    with col_link:
                        # Botón para abrir la página directamente
                        # Abre en pestaña nueva para no salir del dashboard
                        st.link_button("Visitar", res["url"], use_container_width=True)

                st.markdown("")  # separador visual entre tarjetas