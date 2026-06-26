from flask import send_from_directory
import os

def ads_txt():
    # Obtiene la ruta absoluta al directorio raíz del proyecto
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return send_from_directory(root_dir, 'ads.txt')
