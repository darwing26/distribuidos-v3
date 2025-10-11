"""
Módulo de conexión a la base de datos MySQL.
Proporciona una función centralizada para obtener conexiones a la BD.
"""

import pymysql

def get_conn():
    """
    Crea y retorna una conexión a la base de datos MySQL.
    
    Configuración:
    - Host: localhost (127.0.0.1)
    - Puerto: 3306 (puerto por defecto de MySQL)
    - Usuario y contraseña: root/admin1
    - Base de datos: distribuidos_img
    - DictCursor: Los resultados se retornan como diccionarios en lugar de tuplas
    - autocommit=True: Los cambios se guardan automáticamente sin necesidad de commit manual
    
    Returns:
        Connection: Objeto de conexión PyMySQL configurado
    """
    return pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="admin1",
        database="distribuidos_img",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
