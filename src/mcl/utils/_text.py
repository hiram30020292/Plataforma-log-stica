"""Normalización de textos para búsquedas."""

import unicodedata


def normalize_text(text: str) -> str:
    """Pasa a minúsculas, quita acentos y colapsa espacios: ``" Querétaro "`` → ``"queretaro"``.

    Sirve para comparar lo que escribe una persona con los datos sin importar mayúsculas ni
    tildes. La ñ también pierde su tilde (``"Peña"`` → ``"pena"``), igual en ambos lados.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_marks.split())
