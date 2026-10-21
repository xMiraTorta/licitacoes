"""Gravação atômica dos JSONs de dados (coletor/arquivos.py)."""
from __future__ import annotations

import errno
import json
from pathlib import Path

import pytest

from coletor.arquivos import gravar_atomico


def test_grava_e_substitui(tmp_path: Path) -> None:
    alvo = tmp_path / "x.json"
    gravar_atomico(alvo, '{"v": 1}')
    gravar_atomico(alvo, '{"v": 2}')
    assert json.loads(alvo.read_text(encoding="utf-8")) == {"v": 2} and not list(tmp_path.glob("*.tmp"))


def test_falha_no_meio_da_escrita_mantem_o_arquivo_anterior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Disco cheio no meio da escrita: o arquivo final continua inteiro (o anterior) e não sobra temporário."""
    alvo = tmp_path / "x.json"
    alvo.write_text('{"antigo": true}', encoding="utf-8")
    original = Path.write_text

    def pela_metade(self: Path, texto: str, *a: object, **k: object) -> int:
        original(self, texto[: len(texto) // 2], *a, **k)
        raise OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(Path, "write_text", pela_metade)
    with pytest.raises(OSError):
        gravar_atomico(alvo, json.dumps({"novo": list(range(1000))}))
    assert json.loads(alvo.read_text(encoding="utf-8")) == {"antigo": True} and not list(tmp_path.glob("*.tmp"))
