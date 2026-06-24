import json
import os
import re
import shutil
from pathlib import Path
from tqdm import tqdm


def _carregar_configuracao():
    """Carrega o config.json do diretório do script ou do diretório atual."""
    candidatos = []
    try:
        candidatos.append(Path(__file__).resolve().parent / "config.json")
    except NameError:
        pass
    candidatos.append(Path.cwd() / "config.json")

    for caminho in candidatos:
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)

    raise FileNotFoundError("config.json não encontrado")


def _obter_proximo_numero(pasta_raiz):
    """Detecta automaticamente o próximo número sequencial PARA_EDITAR_[N]."""
    numeros = []
    for item in pasta_raiz.iterdir():
        if item.is_dir():
            match = re.match(r"PARA_EDITAR_(\d+)$", item.name, re.IGNORECASE)
            if match:
                numeros.append(int(match.group(1)))
    return max(numeros) + 1 if numeros else 1


def run_organizador_videos():
    """Organiza vídeos em pastas PARA_EDITAR_[N] a partir de config.json."""
    try:
        config = _carregar_configuracao()
    except Exception as e:
        print(f"Erro ao carregar config.json: {e}")
        return

    secao = config.get("organizador_videos_edicao", {})
    root_folder = secao.get("root_folder")
    quantidade_por_pasta = secao.get("quantidade_por_pasta", 10)
    extensoes = secao.get(
        "extensoes",
        [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"],
    )

    if not root_folder:
        print("root_folder não configurado em config.json")
        return

    pasta_raiz = Path(root_folder).expanduser().resolve()
    if not pasta_raiz.exists():
        print(f"Pasta raiz não existe: {pasta_raiz}")
        return

    extensoes_permitidas = {ext.lower().strip() for ext in extensoes}

    videos = [
        item
        for item in pasta_raiz.iterdir()
        if item.is_file() and item.suffix.lower() in extensoes_permitidas
    ]
    videos.sort(key=lambda x: x.name.lower())

    if not videos:
        print("Nenhum vídeo encontrado na pasta raiz.")
        return

    total_batches = (len(videos) + quantidade_por_pasta - 1) // quantidade_por_pasta
    print(f"{len(videos)} vídeo(s) encontrado(s). Criando {total_batches} pasta(s).")

    for i in range(0, len(videos), quantidade_por_pasta):
        lote = videos[i : i + quantidade_por_pasta]
        numero = _obter_proximo_numero(pasta_raiz)
        nome_pasta = f"PARA_EDITAR_{numero}"

        pasta_base = pasta_raiz / nome_pasta
        pasta_para_editar = pasta_base / "PARA_EDITAR"
        pasta_finalizados = pasta_base / "VIDEOS_FINALIZADOS"
        arquivo_log = pasta_base / f"{nome_pasta}.txt"

        pasta_base.mkdir(parents=True, exist_ok=True)
        pasta_para_editar.mkdir(parents=True, exist_ok=True)
        pasta_finalizados.mkdir(parents=True, exist_ok=True)

        for video in tqdm(lote, desc=f"Movendo {nome_pasta}", unit="video"):
            destino = pasta_para_editar / video.name
            try:
                shutil.move(str(video), str(destino))
            except Exception as e:
                print(f"Erro ao mover {video.name}: {e}")

        with open(arquivo_log, "w", encoding="utf-8") as f:
            f.write("\n".join(Path(video.name).stem for video in lote) + "\n")

    print("Organização concluída.")


if __name__ == "__main__":
    run_organizador_videos()