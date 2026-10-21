"""Gravação atômica de arquivos de dados (data.json, mercado.json, marcas_cafe.json): escreve num temporário e
troca pelo nome final de uma vez. Um crash no meio da escrita nunca deixa um JSON pela metade, que o workflow
publicaria e a coleta seguinte não conseguiria ler."""
from __future__ import annotations

import os
from pathlib import Path


def gravar_atomico(path: Path, texto: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(texto, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)  # não deixa o temporário pela metade; o arquivo final continua o anterior
        raise
