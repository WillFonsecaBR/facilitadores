import json
import os
import shutil
from pathlib import Path


def carregar_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def formatar_barra(progresso, tamanho=30):
    preenchido = int(tamanho * progresso)
    vazio = tamanho - preenchido
    return f"[{'#' * preenchido}{'-' * vazio}]"


def nome_unico(destino_raiz, nome_base, extensao):
    contador = 1
    destino = destino_raiz / f"{nome_base}{extensao}"

    while destino.exists():
        destino = destino_raiz / f"{nome_base}_{contador}{extensao}"
        contador += 1

    return destino


def registrar_erro(caminho_log, mensagem):
    with open(caminho_log, "a", encoding="utf-8") as log:
        log.write(mensagem + "\n")


def separar_videos():
    config = carregar_config()
    secao = config["separador_de_videos"]

    root_folder = Path(secao["root_folder"])
    error_log = secao["error_log"]
    allowed_image_ext = {ext.lower() for ext in secao["allowed_image_ext"]}
    allowed_video_ext = {ext.lower() for ext in secao["allowed_video_ext"]}

    if not root_folder.exists():
        print(f"Diretório raiz '{root_folder}' não existe.")
        return

    arquivos = []

    for dirpath, _, filenames in os.walk(root_folder):
        caminho_atual = Path(dirpath)

        if caminho_atual == root_folder:
            continue

        for filename in filenames:
            extensao = Path(filename).suffix.lower()
            if extensao in allowed_image_ext or extensao in allowed_video_ext:
                arquivos.append(caminho_atual / filename)

    total = len(arquivos)

    if total == 0:
        print("Nenhum arquivo de imagem ou vídeo encontrado nas subpastas.")
        return

    print("\nIniciando separação de vídeos e imagens...\n")

    for indice, arquivo_origem in enumerate(arquivos, start=1):
        progresso = indice / total
        barra = formatar_barra(progresso)
        percentual = f"{progresso * 100:6.2f}%"

        print(f"\r{barra} {percentual} ({indice}/{total})", end="", flush=True)

        try:
            nome_base = arquivo_origem.stem
            extensao = arquivo_origem.suffix
            destino = nome_unico(root_folder, nome_base, extensao)

            shutil.move(str(arquivo_origem), str(destino))
        except Exception as e:
            mensagem_erro = f"Erro ao mover '{arquivo_origem}': {e}"
            registrar_erro(error_log, mensagem_erro)

    print("\n\nSeparação concluída.")


if __name__ == "__main__":
    separar_videos()