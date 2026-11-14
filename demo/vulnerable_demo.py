"""PRUEBA DE CODEQL: codigo vulnerable a proposito.

NO se importa desde la app ni se despliega. Existe solo para comprobar que
CodeQL detecta vulnerabilidades. Borrar esta carpeta despues de la prueba.
"""
import subprocess

from fastapi import APIRouter
from sqlalchemy import create_engine, text

router = APIRouter()
engine = create_engine("sqlite:///demo.db")


@router.get("/demo/buscar")
def buscar(nombre: str):
    # VULNERABLE: inyeccion SQL (el parametro se concatena en la consulta)
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT * FROM t_producto WHERE nombre = '{nombre}'")).all()


@router.get("/demo/archivo")
def archivo(ruta: str):
    # VULNERABLE: path traversal (el usuario elige que archivo leer)
    with open("/var/data/" + ruta) as f:
        return f.read()


@router.get("/demo/ping")
def ping(host: str):
    # VULNERABLE: inyeccion de comandos del sistema
    return subprocess.check_output("ping -c 1 " + host, shell=True).decode()
