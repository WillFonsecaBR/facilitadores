import json
import shutil
from pathlib import Path
import hashlib
from datetime import datetime

from PIL import Image
from tqdm import tqdm

try:
    import cv2
except ImportError:
    cv2 = None


CONFIG_FILE = "config.json"
APP_SECTION = "organizador_midias"
OUTPUT_DIR_NAME = "VIDEOS_ORGANIZADOS"


def carregar_config():
    caminho_config = Path(CONFIG_FILE)

    if not caminho_config.exists():
        default_config = {
            APP_SECTION: {
                "root_folder": "/caminho/para/pasta/raiz",
                "error_log": "erros.log",
                "allowed_image_ext": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"],
                "allowed_video_ext": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]
            }
        }

        with open(caminho_config, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)

        print(f"Arquivo {CONFIG_FILE} criado. Ajuste os caminhos e execute novamente.")
        return None

    with open(caminho_config, "r", encoding="utf-8") as f:
        return json.load(f)


def normalizar_texto(texto):
    invalidos = r'<>:"/\|?*'
    for ch in invalidos:
        texto = texto.replace(ch, "_")
    return texto.strip().replace(" ", "_").upper()


def eh_arquivo_auxiliar_mac(path_obj):
    nome = path_obj.name
    return (
        nome.startswith("._") or
        nome == ".DS_Store" or
        nome.startswith(".")
    )


def eh_arquivo_media(caminho_arquivo, config_app):
    if eh_arquivo_auxiliar_mac(caminho_arquivo):
        return False

    extensao = caminho_arquivo.suffix.lower()
    return (
        extensao in config_app["allowed_image_ext"] or
        extensao in config_app["allowed_video_ext"]
    )


def coletar_arquivos_midias(root_folder, config_app):
    arquivos = []
    for caminho_arquivo in root_folder.rglob("*"):
        if caminho_arquivo.is_file() and eh_arquivo_media(caminho_arquivo, config_app):
            arquivos.append(caminho_arquivo)
    return arquivos


def obter_resolucao_imagem(caminho_arquivo):
    try:
        with Image.open(caminho_arquivo) as img:
            return f"{img.width}x{img.height}".upper()
    except Exception:
        return "IMAGE_UNKNOWN"


def obter_resolucao_video(caminho_arquivo):
    try:
        if cv2 is None:
            return "VIDEO_UNKNOWN"

        cap = cv2.VideoCapture(str(caminho_arquivo))
        if not cap.isOpened():
            cap.release()
            return "VIDEO_UNKNOWN"

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        if width > 0 and height > 0:
            return f"{width}x{height}".upper()

        return "VIDEO_UNKNOWN"
    except Exception:
        return "VIDEO_UNKNOWN"


def calcular_hash(caminho_arquivo):
    try:
        hash_obj = hashlib.sha256()
        with open(caminho_arquivo, "rb") as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()[:15].upper()
    except Exception:
        return "HASHERROR000000"


def obter_data(caminho_arquivo):
    try:
        timestamp = caminho_arquivo.stat().st_mtime
        return datetime.fromtimestamp(timestamp).strftime("%Y%m%d")
    except Exception:
        return datetime.now().strftime("%Y%m%d")


def obter_categoria_subcategoria(caminho_arquivo, root_folder):
    categoria = root_folder.name.upper()
    rel = caminho_arquivo.relative_to(root_folder)

    if len(rel.parts) > 1:
        subcategoria = rel.parts[0].upper()
    else:
        subcategoria = categoria

    return categoria, subcategoria


def gerar_nome_base(categoria, subcategoria, resolucao, data, numero, hash_str):
    return f"{categoria}_{subcategoria}_{resolucao}_{data}_{numero}_{hash_str}"


def resolver_duplicado(caminho_saida, nome_base, extensao):
    candidato = caminho_saida / f"{nome_base}{extensao}"
    if not candidato.exists():
        return candidato

    contador = 1
    while True:
        nome_dup = f"{nome_base}_DUP{contador:03d}{extensao}"
        candidato = caminho_saida / nome_dup
        if not candidato.exists():
            return candidato
        contador += 1


def registrar_erro(caminho_log, caminho_arquivo, mensagem):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(caminho_log, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {caminho_arquivo} -> {mensagem}\n")


def mover_arquivo(caminho_origem, caminho_destino):
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)

    try:
        caminho_origem.rename(caminho_destino)
    except OSError:
        shutil.move(str(caminho_origem), str(caminho_destino))


def processar_arquivo(caminho_arquivo, config_app, caminho_saida, numero, total_arquivos):
    root_folder = Path(config_app["root_folder"])

    categoria, subcategoria = obter_categoria_subcategoria(caminho_arquivo, root_folder)
    data = obter_data(caminho_arquivo)
    hash_str = calcular_hash(caminho_arquivo)
    extensao = caminho_arquivo.suffix.lower()

    if extensao in config_app["allowed_image_ext"]:
        resolucao = obter_resolucao_imagem(caminho_arquivo)
    elif extensao in config_app["allowed_video_ext"]:
        resolucao = obter_resolucao_video(caminho_arquivo)
    else:
        resolucao = "UNKNOWN"

    numero_str = str(numero).zfill(len(str(total_arquivos)))
    nome_base = gerar_nome_base(categoria, subcategoria, resolucao, data, numero_str, hash_str)
    caminho_final = resolver_duplicado(caminho_saida, nome_base, extensao)

    mover_arquivo(caminho_arquivo, caminho_final)


def run_organizador():
    config = carregar_config()
    if not config:
        return

    config_app = config.get(APP_SECTION, {})

    root_folder = config_app.get("root_folder")
    error_log = config_app.get("error_log", "erros.log")

    if not root_folder:
        print(f"O campo 'root_folder' não foi definido em '{APP_SECTION}'.")
        return

    root_path = Path(root_folder).expanduser()

    if not root_path.exists() or not root_path.is_dir():
        print(f"ERRO: a pasta raiz não existe ou não é válida: {root_folder}")
        return

    caminho_saida = root_path / OUTPUT_DIR_NAME
    caminho_saida.mkdir(parents=True, exist_ok=True)

    arquivos = coletar_arquivos_midias(root_path, config_app)
    total_arquivos = len(arquivos)

    if total_arquivos == 0:
        print("Nenhum arquivo de imagem ou vídeo encontrado.")
        return

    print(f"Total de arquivos encontrados: {total_arquivos}")
    print(f"Pasta raiz: {root_path}")
    print(f"Pasta de saída: {caminho_saida}")
    print("Iniciando processamento...\n")

    for numero, caminho_arquivo in enumerate(
        tqdm(arquivos, total=total_arquivos, desc="Organizando mídias", unit="arquivo"),
        start=1
    ):
        try:
            processar_arquivo(caminho_arquivo, config_app, caminho_saida, numero, total_arquivos)
        except Exception as e:
            registrar_erro(error_log, caminho_arquivo, str(e))
            print(f"\nErro ao processar {caminho_arquivo}: {e}")

    print("\nConcluído com sucesso.")