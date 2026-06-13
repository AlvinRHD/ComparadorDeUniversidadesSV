"""
PROYECTO FINAL — Comparador de Universidades El Salvador
Archivo: desktop_app.py
Descripción: Aplicación de escritorio (Tkinter) — interfaz ALTERNATIVA/EXTRA
             a streamlit run dashboard.py. Lee el mismo JSON que genera
             crawler.py y muestra una tabla + una gráfica de barras.
Ejecutar: python desktop_app.py
"""

# ═══════════════════════════════════════════════════════════════════
# 📌 MAPEO DE REQUISITOS — desktop_app.py
# ═══════════════════════════════════════════════════════════════════
# 🎨 INTERFAZ (requisito 6): "Aplicación de escritorio (Opcional)"
#     -> Esta app es 100% Tkinter (librería estándar, no requiere instalar nada extra).
#     -> Reutiliza pandas (almacenamiento) y matplotlib (visualización),
#        que ya son parte del proyecto.
#
# 📈 VISUALIZACIÓN:
#     -> Tabla de resultados      -> ttk.Treeview "tabla"
#     -> Gráfica de barras         -> matplotlib embebido con FigureCanvasTkAgg
#
# ⚠️ MANEJO DE ERRORES:
#     -> Carpeta/JSON inexistente -> messagebox.showerror
#     -> Falla al ejecutar crawler.py -> try/except subprocess
# ═══════════════════════════════════════════════════════════════════

import os
import json
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox

import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

CARPETA_RESULTADOS = "resultados"


# ----------------------─
# CARGA DE DATOS (reutiliza la misma lógica que dashboard.py)
# ----------------------─

def cargar_dataframe():
    """Lee el JSON más reciente de resultados/ y devuelve un DataFrame resumen.
    Devuelve None si no hay datos (manejo de errores: datos vacíos)."""
    if not os.path.exists(CARPETA_RESULTADOS):
        return None

    archivos = sorted(
        [f for f in os.listdir(CARPETA_RESULTADOS) if f.endswith(".json")],
        reverse=True
    )
    if not archivos:
        return None

    ruta = os.path.join(CARPETA_RESULTADOS, archivos[0])
    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)

    resumen = []
    for siglas, d in datos.items():
        resumen.append({
            "Siglas":            siglas,
            "Universidad":       d["nombre"],
            "Páginas visitadas": d["paginas_visitadas"],
            "Coincidencias":     d["coincidencias"],
            "Correos":           len(d.get("correos", [])),
            "Teléfonos":         len(d.get("telefonos", [])),
        })

    return pd.DataFrame(resumen), archivos[0]


# ----------------------─
# APP PRINCIPAL
# ----------------------─

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎓 Comparador de Universidades — El Salvador (App de escritorio)")
        self.geometry("950x650")

        # - Barra superior con botones -
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=10, pady=8)

        ttk.Button(barra, text="🔄 Actualizar datos", command=self.refrescar).pack(side="left")
        ttk.Button(barra, text="🕷️ Ejecutar crawler.py", command=self.ejecutar_crawler).pack(side="left", padx=8)

        self.lbl_archivo = ttk.Label(barra, text="")
        self.lbl_archivo.pack(side="right")

        # - Tabla de resultados -
        columnas = ["Siglas", "Universidad", "Páginas visitadas", "Coincidencias", "Correos", "Teléfonos"]
        self.tabla = ttk.Treeview(self, columns=columnas, show="headings", height=8)
        for col in columnas:
            self.tabla.heading(col, text=col)
            self.tabla.column(col, width=120 if col != "Universidad" else 280, anchor="center")
        self.tabla.pack(fill="x", padx=10, pady=8)

        # - Área de la gráfica -
        self.frame_grafica = ttk.Frame(self)
        self.frame_grafica.pack(fill="both", expand=True, padx=10, pady=8)
        self.canvas = None

        self.refrescar()

    # - Cargar/recargar datos y refrescar tabla + gráfica -
    def refrescar(self):
        resultado = cargar_dataframe()

        if resultado is None:
            # ⚠️ REQUISITO: manejo de errores -> datos vacíos / sin resultados
            messagebox.showerror(
                "Sin datos",
                "No existe 'resultados/' o está vacío.\n"
                "Ejecutá primero el crawler (botón 'Ejecutar crawler.py')."
            )
            return

        df, archivo = resultado
        self.lbl_archivo.config(text=f"Archivo: {archivo}")

        # Limpiar tabla
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)
        for _, r in df.iterrows():
            self.tabla.insert("", "end", values=list(r))

        self.dibujar_grafica(df)

    # - Gráfica de barras (requisito visualización) -
    def dibujar_grafica(self, df):
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(df["Siglas"], df["Coincidencias"], color="#3b82f6")
        ax.set_title("Palabras clave encontradas por universidad")
        ax.set_xlabel("Universidad")
        ax.set_ylabel("Coincidencias")
        fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(fig, master=self.frame_grafica)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)  # evitar fugas de memoria al refrescar varias veces

    # - Ejecutar crawler.py en un proceso aparte -
    def ejecutar_crawler(self):
        try:
            messagebox.showinfo("Crawler", "Se ejecutará crawler.py. Esto puede tardar unos segundos...")
            subprocess.run([sys.executable, "crawler.py"], check=True)
            messagebox.showinfo("Listo", "Crawler finalizado. Actualizando datos...")
            self.refrescar()
        except Exception as e:
            # ⚠️ REQUISITO: manejo de errores -> falla al ejecutar el crawler
            messagebox.showerror("Error", f"No se pudo ejecutar crawler.py:\n{e}")


if __name__ == "__main__":
    App().mainloop()