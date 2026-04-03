import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from PIL import Image
from tqdm import tqdm

try:
    import cv2
except ImportError:
    cv2 = None


CONFIG_FILE = "config.json"
APP_SECTION = "organizador_midias"


def load_config():
    config_path = Path(CONFIG_FILE)

    default_config = {
        APP_SECTION: {
            "root_folder": "/Users/willianfonseca/Desktop/SUA_PASTA_AQUI",
            "move_to_root": False,
            "error_log": "errors.log",
            "allowed_image_ext": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"],
            "allowed_video_ext": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]
        }
    }

    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        print(f"Arquivo {CONFIG_FILE} criado. Edite o caminho e execute novamente.")
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Erro ao ler {CONFIG_FILE}: {e}")
        return None


def normalize_text(text):
    invalid_chars = r'<>:"/\|?*'
    for ch in invalid_chars:
        text = text.replace(ch, "_")
    return text.strip().replace(" ", "_").upper()


def is_media_file(file_path, app_config):
    ext = file_path.suffix.lower()
    return ext in app_config["allowed_image_ext"] or ext in app_config["allowed_video_ext"]


def get_resolution(file_path):
    ext = file_path.suffix.lower()

    try:
        if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"]:
            with Image.open(file_path) as img:
                width, height = img.size
                return f"{width}x{height}".upper()

        if ext in [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]:
            if cv2 is None:
                return "VIDEO_UNKNOWN"

            cap = cv2.VideoCapture(str(file_path))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()

            if width > 0 and height > 0:
                return f"{width}x{height}".upper()
            return "VIDEO_UNKNOWN"

    except Exception:
        return "UNKNOWN"

    return "UNKNOWN"


def get_download_date(file_path):
    try:
        stat = file_path.stat()
        ts = getattr(stat, "st_birthtime", stat.st_ctime)
        return datetime.fromtimestamp(ts).strftime("%Y%m%d")
    except Exception:
        return datetime.now().strftime("%Y%m%d")


def get_unique_hash(file_path):
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()[:15].upper()
    except Exception:
        return "HASHERROR000000"


def get_all_media_files(root_path, app_config):
    media_files = []
    for path in root_path.rglob("*"):
        if path.is_file() and is_media_file(path, app_config):
            media_files.append(path)
    return media_files


def build_new_name(categoria, subcategoria, resolucao, data_download, numero, hash_unico, ext):
    return (
        f"{normalize_text(categoria)}_"
        f"{normalize_text(subcategoria)}_"
        f"{normalize_text(resolucao)}_"
        f"{data_download}_"
        f"{numero}_"
        f"{hash_unico}"
        f"{ext.lower()}"
    )


def safe_move_or_rename(src, dst):
    if not dst.exists():
        src.rename(dst)
        return dst

    base = dst.stem
    ext = dst.suffix
    counter = 1

    while True:
        candidate = dst.parent / f"{base}_{counter}{ext}"
        if not candidate.exists():
            src.rename(candidate)
            return candidate
        counter += 1


def log_error(error_log_path, file_path, error_message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(error_log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {file_path} -> {error_message}\n")


def run_organizador():
    config = load_config()
    if not config:
        return

    app_config = config.get(APP_SECTION, {})

    root_folder = app_config.get("root_folder")
    move_to_root = bool(app_config.get("move_to_root", False))
    error_log = app_config.get("error_log", "errors.log")

    if not root_folder:
        print(f"O campo 'root_folder' não foi definido em '{APP_SECTION}' no config.json.")
        return

    root_path = Path(root_folder).expanduser()

    if not root_path.exists() or not root_path.is_dir():
        print(f"ERRO: a pasta informada não existe ou não é válida: {root_folder}")
        return

    categoria = root_path.name
    media_files = get_all_media_files(root_path, app_config)
    total_files = len(media_files)

    if total_files == 0:
        print("Nenhum arquivo de imagem ou vídeo encontrado.")
        return

    largura_numero = len(str(total_files))

    print(f"Total de arquivos encontrados: {total_files}")
    print(f"Pasta raiz: {root_path}")
    print("Iniciando processamento...\n")

    for index, file_path in enumerate(
        tqdm(media_files, total=total_files, desc="Processando arquivos", unit="arquivo"),
        start=1
    ):
        try:
            subcategoria = file_path.parent.name if file_path.parent != root_path else "ROOT"
            resolucao = get_resolution(file_path)
            data_download = get_download_date(file_path)
            hash_unico = get_unique_hash(file_path)
            numero = str(index).zfill(largura_numero)

            novo_nome = build_new_name(
                categoria=categoria,
                subcategoria=subcategoria,
                resolucao=resolucao,
                data_download=data_download,
                numero=numero,
                hash_unico=hash_unico,
                ext=file_path.suffix
            )

            destino = root_path / novo_nome if move_to_root else file_path.parent / novo_nome
            safe_move_or_rename(file_path, destino)

        except Exception as e:
            log_error(error_log, file_path, str(e))
            print(f"\nErro ao processar {file_path}: {e}")

    print("\nConcluído com sucesso.")