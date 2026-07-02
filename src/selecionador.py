# =============================================================================
# Funcionamento geral do script:
# Este script lê configurações de um config.json localizado na raiz do repositório.
# Localiza nichos (subpastas) dentro de uma pasta raiz configurada, move imagens
# com extensões permitidas para uma estrutura de pastas separada por nicho dentro
# de uma pasta de saída, conta os vídeos restantes por nicho, registra logs gerais
# na pasta 'logs' e logs de erro na pasta 'error', e imprime um relatório por nicho
# ao final do processamento.
# =============================================================================

import json
import os
import shutil
from tqdm import tqdm
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)
CONFIG_PATH = os.path.join(REPO_ROOT, 'config.json')

def run_selecionador():
    # 1. Carregar configurações dinamicamente
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config_full = json.load(f)
    except Exception as e:
        print(f"Erro ao ler config.json: {e}")
        return

    if 'selecionador_imagens' not in config_full:
        print("Erro: A seção 'selecionador_imagens' não existe no config.json.")
        return

    cfg = config_full['selecionador_imagens']
    root = cfg.get('root_folder')
    output_folder_name = cfg.get('output_folder_name', 'IMAGENS_SEPARADAS')
    log_file = cfg.get('error_log', 'log_selecionador.txt')
    allowed_img_ext = set(ext.lower() for ext in cfg.get('allowed_image_ext', []))

    allowed_video_ext = set()
    for section in ['organizador_midias', 'separador_de_videos']:
        if section in config_full:
            allowed_video_ext.update(ext.lower() for ext in config_full[section].get('allowed_video_ext', []))

    if not root or not os.path.exists(root):
        print(f"Erro: Caminho raiz não encontrado: {root}")
        return

    logs_dir = os.path.join(REPO_ROOT, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    log_file_path = os.path.join(logs_dir, log_file)

    logging.basicConfig(filename=log_file_path, level=logging.INFO, 
                        format='%(asctime)s - %(message)s', encoding='utf-8')

    error_dir = os.path.join(REPO_ROOT, 'error')
    os.makedirs(error_dir, exist_ok=True)
    error_log_path = os.path.join(error_dir, 'erros_selecionador.txt')
    error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logging.getLogger().addHandler(error_handler)

    dest_base = os.path.join(root, output_folder_name)
    os.makedirs(dest_base, exist_ok=True)

    nichos = [d for d in os.listdir(root) 
              if os.path.isdir(os.path.join(root, d)) and d != output_folder_name]

    print(f"Iniciando processamento em: {root}\n")

    for nicho in nichos:
        nicho_path = os.path.join(root, nicho)
        nicho_dest_dir = os.path.join(dest_base, nicho)
        os.makedirs(nicho_dest_dir, exist_ok=True)

        imagens = []
        for r, d, f in os.walk(nicho_path):
            if output_folder_name in r: continue
            for file in f:
                if any(file.lower().endswith(ext) for ext in allowed_img_ext):
                    imagens.append(os.path.join(r, file))

        img_movidas_nicho = 0
        if imagens:
            pbar = tqdm(imagens, desc=f"Nicho: {nicho}", unit="img")
            for src_path in pbar:
                filename = os.path.basename(src_path)
                dst_path = os.path.join(nicho_dest_dir, filename)
                
                if os.path.exists(dst_path):
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(os.path.join(nicho_dest_dir, f"{name}_{counter}{ext}")):
                        counter += 1
                    dst_path = os.path.join(nicho_dest_dir, f"{name}_{counter}{ext}")

                try:
                    shutil.move(src_path, dst_path)
                    img_movidas_nicho += 1
                except Exception as e:
                    logging.error(f"Erro ao mover {filename} em {nicho}: {e}")

        video_count = 0
        for r, d, f in os.walk(nicho_path):
            if output_folder_name in r: continue
            for file in f:
                if any(file.lower().endswith(ext) for ext in allowed_video_ext):
                    video_count += 1
        
        resultado = f"Nicho [{nicho}]: {img_movidas_nicho} imagens movidas | {video_count} vídeos restantes"
        print(resultado)
        logging.info(resultado)

    print(f"\nProcesso concluído. Log detalhado em: {log_file}")

if __name__ == "__main__":
    run_selecionador()