"""
PROYECTO FINAL - Comparador de Universidades El Salvador
Archivo: crawler.py
Descripción: Crawlea universidades, extrae datos (palabras clave, correos,
             teléfonos, imágenes), guarda JSON con timestamp, archivos por
             carpeta y registra en MySQL.
Ejecutar: python crawler.py
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
from database import conectar, insertar_universidad, cerrar

# ═══════════════════════════════════════════════════════════════════
# 📌 MAPEO DE REQUISITOS - crawler.py
# ═══════════════════════════════════════════════════════════════════
# 🕷️ CRAWLER AUTOMÁTICO (obligatorio) -> función crawlear_universidad()
#     ✅ Inicia desde una URL principal      -> url_inicial = info["url"]
#     ✅ Navega enlaces internos              -> bucle "Recolectar enlaces internos"
#     ✅ Evita URLs repetidas                 -> set "visitadas" + chequeo en "pendientes"
#     ✅ Limita páginas visitadas             -> MAX_PAGINAS / while len(visitadas) < MAX_PAGINAS
#     ✅ Maneja errores de conexión           -> try/except + chequeo status_code
#     ✅ Muestra progreso en consola          -> prints "[OK] Visitando..." / "Enlaces encontrados"
#
# 📄 WEB SCRAPING (obligatorio, mínimo 3 tipos -> aquí hay 5):
#     ✅ Títulos       -> soup.title (dentro del bucle de palabras clave)
#     ✅ Correos       -> extraer_correos()
#     ✅ Teléfonos     -> extraer_telefonos()
#     ✅ Imágenes      -> descargar_imagenes()
#     ✅ Enlaces       -> recolección de <a href> internos
#
# 💾 ALMACENAMIENTO (obligatorio):
#     ✅ JSON con timestamp -> bloque MAIN, json.dump(comparacion, ...)
#     ✅ DataFrame de pandas -> se construye en dashboard.py a partir de este JSON
#     ⭐ MySQL (extra)       -> insertar_universidad() en bloque MAIN
#
# ⚠️ MANEJO DE ERRORES (obligatorio):
#     ✅ Conexiones fallidas / URLs inválidas -> try/except Exception en crawlear_universidad()
#     ✅ Páginas inexistentes (HTTP != 200)   -> chequeo resp.status_code != 200
#     ✅ Datos vacíos                          -> sets/listas vacías por defecto, dashboard valida con .empty
# ═══════════════════════════════════════════════════════════════════

# ----------------------─
# UNIVERSIDADES DE EL SALVADOR (26 autorizadas)
# Para demo: solo las marcadas con DEMO=True se crawlean.
# Cambiá MAX_PAGINAS y el filtro para correr todas.
# ----------------------─

UNIVERSIDADES = {
    "UNIVO": {"url": "https://www.univo.edu.sv/",                  "nombre": "Universidad de Oriente",                           "lat":  13.4801, "lng": -88.1775, "demo": False},
    "UGB":   {"url": "https://www.ugb.edu.sv/",                    "nombre": "Universidad Capitán General Gerardo Barrios",       "lat":  13.4834, "lng": -88.1789, "demo": False},
    "UES":   {"url": "https://www.ues.edu.sv/",                    "nombre": "Universidad de El Salvador",                        "lat":  13.7176, "lng": -89.2016, "demo": True},
    "UNAB":  {"url": "https://www.unab.edu.sv/",                   "nombre": "Universidad Andrés Bello",                         "lat":  13.6921, "lng": -89.2231, "demo": False},
    "UDB":   {"url": "https://www.udb.edu.sv/",                    "nombre": "Universidad Don Bosco",                             "lat":  13.7080, "lng": -89.1730, "demo": True},
    
    "UCA":   {"url": "https://www.uca.edu.sv/",                    "nombre": "Universidad Centroamericana José Simeón Cañas",     "lat":  13.6763, "lng": -89.2389, "demo": True},
   
    "UTEC":  {"url": "https://www.utec.edu.sv/",                   "nombre": "Universidad Tecnológica de El Salvador",            "lat":  13.6986, "lng": -89.1910, "demo": True},
    "UJMD":  {"url": "https://www.ujmd.edu.sv/",                   "nombre": "Universidad Dr. José Matías Delgado",               "lat":  13.6698, "lng": -89.2512, "demo": False},
    "UEES":  {"url": "https://www.uees.edu.sv/",                   "nombre": "Universidad Evangélica de El Salvador",             "lat":  13.7005, "lng": -89.2198, "demo": False},
    "UMA":   {"url": "https://www.uma.edu.sv/",                    "nombre": "Universidad Modular Abierta",                      "lat":  13.6950, "lng": -89.1880, "demo": False},
    "USAM":  {"url": "https://www.usam.edu.sv/",                   "nombre": "Universidad Salvadoreña Alberto Masferrer",         "lat":  13.7012, "lng": -89.1956, "demo": False},
    "UPED":  {"url": "https://www.universidadpedagogica.com/",     "nombre": "Universidad Pedagógica de El Salvador",             "lat":  13.7020, "lng": -89.2100, "demo": False},
    "UAE":   {"url": "https://www.uae.edu.sv/",                    "nombre": "Universidad Albert Einstein",                      "lat":  13.7035, "lng": -89.2090, "demo": False},
    "UFG":   {"url": "https://www.ufg.edu.sv/",                    "nombre": "Universidad Francisco Gavidia",                     "lat":  13.6994, "lng": -89.1914, "demo": True},
    "UPES":  {"url": "https://www.upes.edu.sv/",                   "nombre": "Universidad Politécnica de El Salvador",           "lat":  13.6978, "lng": -89.1923, "demo": False},
    "UPAN":  {"url": "https://www.upan.edu.sv/",                   "nombre": "Universidad Panamericana de El Salvador",          "lat":  13.6890, "lng": -89.2340, "demo": False},
    "ULS":   {"url": "https://www.uls.edu.sv/",                    "nombre": "Universidad Luterana Salvadoreña",                 "lat":  13.6912, "lng": -89.2156, "demo": False},
    "UTLA":  {"url": "https://www.utla.edu.sv/",                   "nombre": "Universidad Técnica Latinoamericana",              "lat":  13.6745, "lng": -89.2890, "demo": False},
    "ITCA":  {"url": "https://www.itca.edu.sv/",                   "nombre": "Escuela Especializada en Ingeniería ITCA-FEPADE",  "lat":  13.7101, "lng": -89.1812, "demo": False},
    "UNSSA": {"url": "https://www.unssa.edu.sv/",                  "nombre": "Universidad Nueva San Salvador",                   "lat":  13.6734, "lng": -89.2876, "demo": False},
    "USO":   {"url": "https://www.usonsonate.edu.sv/",             "nombre": "Universidad de Sonsonate",                        "lat":  13.7189, "lng": -89.7239, "demo": False},
    "UNICO": {"url": "https://www.unico.edu.sv/",                  "nombre": "Universidad de El Salvador Occidente",             "lat":  13.9894, "lng": -89.5530, "demo": False},
    "UNASA": {"url": "https://www.unasa.edu.sv/",                  "nombre": "Universidad Autónoma de Santa Ana",                "lat":  13.9958, "lng": -89.5596, "demo": False},
    "ESEN":  {"url": "https://www.esen.edu.sv/",                   "nombre": "Escuela Superior de Economía y Negocios",          "lat":  13.6812, "lng": -89.2445, "demo": False},
    "UCAD":  {"url": "https://www.ucad.edu.sv/",                   "nombre": "Universidad Católica de El Salvador",              "lat":  13.8956, "lng": -89.6590, "demo": False},
    "UNICAES":{"url": "https://www.unicaes.edu.sv/",               "nombre": "Universidad Católica de El Salvador Santa Ana",    "lat":  13.9978, "lng": -89.5601, "demo": False},
}

# Cambiá a False para correr TODAS las universidades
SOLO_DEMO    = True
MAX_PAGINAS  = 3
PAUSA        = 0.5

# Carpetas de salida
CARPETA_RESULTADOS = "resultados"
CARPETA_IMAGENES   = "imagenes_descargadas"
CARPETA_CONTACTOS  = "contactos"

# Regex para correos y teléfonos
RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
RE_PHONE = re.compile(r"(?:\+503[\s\-]?)?(?:2|6|7)\d{3}[\s\-]?\d{4}")

# Palabras clave académicas
PALABRAS_CLAVE = [
    "carrera", "ingeniería", "ingenieria", "facultad",
    "maestría", "maestria", "técnico", "tecnico",
    "licenciatura", "pregrado", "posgrado",
    "administración", "administracion", "derecho",
    "medicina", "arquitectura", "computación", "computacion"
]
NORMALIZACIONES = {
    "ingenieria": "ingeniería", "maestria": "maestría",
    "tecnico": "técnico", "administracion": "administración",
    "computacion": "computación"
}

# Formatos de imagen aceptados
FORMATOS_IMG = {".jpg", ".jpeg", ".png", ".webp"}


# ----------------------─
# SCRAPING - Correos, teléfonos, imágenes
# ----------------------─

def extraer_correos(html, soup):
    """Extrae correos del HTML y atributos mailto."""
    # 📄 REQUISITO Web Scraping: extracción de correos (tipo de dato #1)
    correos = set(RE_EMAIL.findall(html))
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("mailto:"):
            correos.add(a["href"].replace("mailto:", "").split("?")[0].strip())
    # Filtrar extensiones de imagen que coincidan con el regex
    return [e for e in correos if not any(e.endswith(x) for x in [".png",".jpg",".gif",".svg"])]


def extraer_telefonos(texto):
    """Extrae teléfonos con formato salvadoreño."""
    # 📄 REQUISITO Web Scraping: extracción de teléfonos (tipo de dato #2)
    return list(set(RE_PHONE.findall(texto)))


def descargar_imagenes(soup, url_base, siglas):
    """Descarga las primeras 10 imágenes válidas (PNG/JPG/WEBP)."""
    # 📄 REQUISITO Web Scraping: extracción/descarga de imágenes (tipo de dato #3)
    carpeta = os.path.join(CARPETA_IMAGENES, siglas)
    os.makedirs(carpeta, exist_ok=True)

    descargadas = 0
    for tag in soup.find_all("img", src=True):
        if descargadas >= 10:
            break
        src = tag.get("src", "")
        url_img = urljoin(url_base, src)
        ext = os.path.splitext(urlparse(url_img).path)[1].lower()

        if ext not in FORMATOS_IMG:
            continue
        try:
            contenido = requests.get(url_img, timeout=8).content
            nombre    = f"{siglas}_{descargadas + 1}{ext}"
            with open(os.path.join(carpeta, nombre), "wb") as f:
                f.write(contenido)
            descargadas += 1
        except Exception:
            continue

    if descargadas:
        print(f"    📷 {descargadas} imágenes guardadas en {carpeta}/")


def guardar_contactos(siglas, nombre, correos, telefonos):
    """Guarda correos y teléfonos en JSON por universidad."""
    os.makedirs(CARPETA_CONTACTOS, exist_ok=True)
    datos = {
        "universidad": nombre,
        "siglas":      siglas,
        "correos":     correos,
        "telefonos":   telefonos
    }
    ruta = os.path.join(CARPETA_CONTACTOS, f"{siglas}_contactos.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)
    print(f"    📧 Contactos guardados en {ruta}")


# ----------------------─
# CRAWLER POR UNIVERSIDAD
# ----------------------─

def crawlear_universidad(siglas, info):
    """Recorre el sitio, detecta palabras clave y extrae contactos e imágenes."""
    # 🕷️ REQUISITO Crawler: "Inicia desde una URL principal"
    url_inicial = info["url"]
    dominio     = urlparse(url_inicial).netloc
    nombre      = info["nombre"]

    # 🕷️ REQUISITO Crawler: "Evita URLs repetidas"
    #     -> visitadas guarda lo ya recorrido, pendientes es la cola de URLs a visitar
    visitadas  = set()
    pendientes = [url_inicial]
    resultados = []
    todos_correos   = set()
    todos_telefonos = set()
    imagenes_ok = False  # solo descargamos imágenes de la primera página

    print(f"\n{'='*58}")
    print(f"  {siglas} - {nombre}")
    print(f"{'='*58}")

    while pendientes and len(visitadas) < MAX_PAGINAS:  # 🕷️ REQUISITO: "Limita la cantidad de páginas visitadas"
        url_actual = pendientes.pop(0)

        if url_actual in visitadas:
            continue

        # 🕷️ REQUISITO: "Mostrar en consola el progreso del recorrido"
        print(f"  [OK] Visitando página: {url_actual}")
        visitadas.add(url_actual)

        try:  # ⚠️ REQUISITO: manejo de errores de conexión
            resp = requests.get(
                url_actual, timeout=10,
                headers={"User-Agent": "UniSVCrawler/1.0"}
            )
            if resp.status_code != 200:
                # ⚠️ REQUISITO: manejo de "páginas inexistentes" (HTTP distinto de 200)
                print(f"       HTTP {resp.status_code} - omitida")
                continue

            soup  = BeautifulSoup(resp.text, "lxml")
            texto = soup.get_text()

            # Palabras clave
            palabras_encontradas = set()
            texto_lower = texto.lower()
            for palabra in PALABRAS_CLAVE:
                if palabra in texto_lower:
                    display = NORMALIZACIONES.get(palabra, palabra)
                    if display not in palabras_encontradas:
                        palabras_encontradas.add(display)
                        # 📄 REQUISITO Web Scraping: extracción de TÍTULOS (tipo de dato #4)
                        titulo = soup.title.text.strip() if soup.title else ""
                        resultados.append({"palabra": display, "url": url_actual, "titulo": titulo})

            if palabras_encontradas:
                print(f"       ✓ {', '.join(sorted(palabras_encontradas))}")

            # Correos y teléfonos
            todos_correos.update(extraer_correos(resp.text, soup))
            todos_telefonos.update(extraer_telefonos(texto))

            # Imágenes (solo primera página)
            if not imagenes_ok:
                descargar_imagenes(soup, url_actual, siglas)
                imagenes_ok = True

            # 🕷️ REQUISITO Crawler: "Navega automáticamente por enlaces internos"
            # 📄 REQUISITO Web Scraping: extracción de ENLACES (tipo de dato #5)
            enlaces = soup.find_all("a", href=True)
            print(f"       [OK] Enlaces encontrados: {len(enlaces)}")  # progreso en consola
            for enlace in enlaces:
                href = enlace.get("href", "")
                if href.startswith("#") or href.startswith("javascript"):
                    continue
                url_completa = urljoin(url_actual, href)
                if (dominio in urlparse(url_completa).netloc
                        and url_completa not in visitadas
                        and url_completa not in pendientes):
                    pendientes.append(url_completa)

        except Exception as e:
            # ⚠️ REQUISITO: manejo de errores de conexión / URLs inválidas
            print(f"       Error: {e}")

        time.sleep(PAUSA)

    correos_lista   = list(todos_correos)
    telefonos_lista = list(todos_telefonos)

    # Guardar contactos en carpeta
    guardar_contactos(siglas, nombre, correos_lista, telefonos_lista)

    print(f"  Finalizado: {len(visitadas)} páginas | {len(resultados)} coincidencias | "
          f"{len(correos_lista)} correos | {len(telefonos_lista)} teléfonos")

    return {
        "siglas":            siglas,
        "nombre":            nombre,
        "paginas_visitadas": len(visitadas),
        "coincidencias":     len(resultados),
        "resultados":        resultados,
        "correos":           correos_lista,
        "telefonos":         telefonos_lista,
        "lat":               info["lat"],
        "lng":               info["lng"],
    }


# ----------------------─
# MAIN
# ----------------------─

if __name__ == "__main__":
    # Filtrar universidades según modo demo
    unis = {k: v for k, v in UNIVERSIDADES.items() if not SOLO_DEMO or v["demo"]}

    print("="*58)
    print("  COMPARADOR DE UNIVERSIDADES - EL SALVADOR")
    print("="*58)
    print(f"  Universidades a crawlear: {len(unis)}")
    print(f"  Páginas por universidad:  {MAX_PAGINAS}")
    print(f"  Pausa entre requests:     {PAUSA}s")
    print(f"  Modo demo:                {'Sí (5 unis)' if SOLO_DEMO else 'No (todas)'}")
    print("="*58)

    # Conectar a MySQL
    conn = conectar()

    comparacion = {}
    for siglas, info in unis.items():
        data = crawlear_universidad(siglas, info)
        comparacion[siglas] = data

        # ⭐ REQUISITO EXTRA: Almacenamiento en base de datos MySQL
        insertar_universidad(
            conn, siglas, data,
            data["correos"], data["telefonos"],
            {"lat": data["lat"], "lng": data["lng"]}
        )

    cerrar(conn)

    # 💾 REQUISITO: Almacenamiento de datos -> JSON con timestamp
    #     (a partir de este JSON, dashboard.py construye los DataFrames de pandas)
    os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo   = os.path.join(CARPETA_RESULTADOS, f"resultados_{timestamp}.json")

    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(comparacion, f, ensure_ascii=False, indent=4)

    print(f"\n{'='*58}")
    print(f"  JSON guardado en:  {archivo}")
    print(f"  Imágenes en:       {CARPETA_IMAGENES}/")
    print(f"  Contactos en:      {CARPETA_CONTACTOS}/")
    print(f"  Ejecutá:           streamlit run dashboard.py")
    print("="*58)