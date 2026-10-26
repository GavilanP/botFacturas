"""Arranca la web de tesorería en local (solo en este equipo).

Escucha SOLO en 127.0.0.1: nadie más de la red puede entrar (sin login, v1).
Uso:  python src/run_web.py     ->   http://127.0.0.1:8000
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=False)
