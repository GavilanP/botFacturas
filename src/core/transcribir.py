"""Transcripción de notas de voz a texto con Whisper local (mlx-whisper).

Todo corre en el propio Mac (Apple Silicon); el audio nunca sale de la máquina.
La primera vez, mlx-whisper descarga el modelo a ~/.cache/huggingface (~1,5 GB
para large-v3-turbo) y lo reutiliza en adelante.

Las notas de voz de Telegram llegan como bytes en OGG/Opus; Whisper las lee a
través de ffmpeg, que debe estar instalado (brew install ffmpeg).
"""
from __future__ import annotations

import tempfile

MODELO_POR_DEFECTO = "mlx-community/whisper-large-v3-turbo"


def transcribir_fichero(ruta, modelo: str = MODELO_POR_DEFECTO) -> str:
    """Transcribe un fichero de audio a texto en español."""
    import mlx_whisper  # import perezoso: no cargar MLX si el audio está desactivado

    resultado = mlx_whisper.transcribe(str(ruta), path_or_hf_repo=modelo, language="es")
    return resultado["text"].strip()


def transcribir_bytes(contenido: bytes, extension: str = "ogg",
                      modelo: str = MODELO_POR_DEFECTO) -> str:
    """Transcribe audio recibido en memoria (p. ej. una nota de voz de Telegram).

    Whisper/ffmpeg leen de fichero, así que se vuelca a un temporal que se borra solo.
    """
    with tempfile.NamedTemporaryFile(suffix=f".{extension}") as tmp:
        tmp.write(contenido)
        tmp.flush()
        return transcribir_fichero(tmp.name, modelo)
