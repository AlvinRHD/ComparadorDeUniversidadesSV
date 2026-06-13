"""
PROYECTO FINAL — Comparador de Universidades El Salvador
Archivo: database.py
Descripción: Conexión a MySQL, creación automática de BD y tabla,
             e inserción de registros scrapeados.
"""

import mysql.connector
from mysql.connector import Error

# ═══════════════════════════════════════════════════════════════
# 📌 MAPEO DE REQUISITOS — database.py
# ═══════════════════════════════════════════════════════════════
# ⭐ EXTRA (puntos opcionales): Almacenamiento en base de datos MySQL
#     -> conectar()            : crea la BD y la tabla si no existen
#     -> insertar_universidad(): guarda un registro por universidad
#     -> cerrar()              : cierra la conexión
#
# ⚠️ Manejo de errores (obligatorio):
#     -> Conexiones fallidas a MySQL  -> try/except en conectar()
#     -> Inserciones fallidas / datos vacíos -> try/except en
#        insertar_universidad() (usa .get() y listas vacías por defecto)
# ═══════════════════════════════════════════════════════════════

# ----------------------─
# CONFIGURACIÓN DE CONEXIÓN
# ----------------------─

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",       # cambiá si tu usuario es diferente
    "password": "()(delyal)",           # tu contraseña de MySQL Workbench
    "charset":  "utf8mb4"
}

DB_NAME = "universidades_sv"

# ----------------------─
# CREAR BASE DE DATOS Y TABLA AUTOMÁTICAMENTE
# ----------------------─

SQL_CREAR_BD = f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"

SQL_CREAR_TABLA = """
CREATE TABLE IF NOT EXISTS paginas_universidades (
    id                        INT AUTO_INCREMENT PRIMARY KEY,
    universidad               VARCHAR(255),
    siglas                    VARCHAR(20),
    url                       TEXT,
    titulo                    TEXT,
    descripcion               TEXT,
    correos                   TEXT,
    telefonos                 TEXT,
    palabras_clave            TEXT,
    cantidad_coincidencias    INT DEFAULT 0,
    cantidad_paginas          INT DEFAULT 0,
    latitud                   DECIMAL(10,6),
    longitud                  DECIMAL(10,6),
    fecha_registro            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def conectar():
    """Crea conexión a MySQL y asegura que la BD y tabla existan."""
    try:
        # Conectar sin especificar BD primero
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Crear BD si no existe
        cursor.execute(SQL_CREAR_BD)
        cursor.execute(f"USE {DB_NAME}")

        # Crear tabla si no existe
        cursor.execute(SQL_CREAR_TABLA)
        conn.commit()

        print(f"  [DB] Conectado a MySQL — base de datos: {DB_NAME}")
        return conn

    except Error as e:
        # ⚠️ REQUISITO: manejo de errores -> conexión fallida a MySQL
        print(f"  [DB ERROR] No se pudo conectar a MySQL: {e}")
        return None


# ----------------------─
# INSERTAR RESULTADOS DE UNA UNIVERSIDAD
# ----------------------─

SQL_INSERTAR = """
INSERT INTO paginas_universidades (
    universidad, siglas, url, titulo, descripcion,
    correos, telefonos, palabras_clave,
    cantidad_coincidencias, cantidad_paginas,
    latitud, longitud
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def insertar_universidad(conn, siglas, data, correos, telefonos, coordenadas):
    """Inserta un registro por universidad en la tabla."""
    if conn is None:
        return

    try:
        cursor = conn.cursor()

        # Armar listas como texto separado por comas
        palabras = ", ".join(set(r["palabra"] for r in data["resultados"]))
        correos_txt   = ", ".join(correos)
        telefonos_txt = ", ".join(telefonos)

        # URL y título de la página principal (primer resultado)
        url_principal   = data["resultados"][0]["url"]   if data["resultados"] else ""
        titulo_principal = data["resultados"][0]["titulo"] if data["resultados"] else ""

        lat = coordenadas.get("lat")
        lng = coordenadas.get("lng")

        cursor.execute(SQL_INSERTAR, (
            data["nombre"],
            siglas,
            url_principal,
            titulo_principal,
            "",                          # descripcion (se puede ampliar)
            correos_txt,
            telefonos_txt,
            palabras,
            data["coincidencias"],
            data["paginas_visitadas"],
            lat,
            lng
        ))
        conn.commit()
        print(f"  [DB] Guardado: {data['nombre']}")

    except Error as e:
        # ⚠️ REQUISITO: manejo de errores -> fallo al insertar en MySQL
        print(f"  [DB ERROR] Al insertar {siglas}: {e}")


# ----------------------─
# CERRAR CONEXIÓN
# ----------------------─

def cerrar(conn):
    """Cierra la conexión a MySQL."""
    if conn and conn.is_connected():
        conn.close()
        print("  [DB] Conexión cerrada.")