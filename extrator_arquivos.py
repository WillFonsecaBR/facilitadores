import json
import os
import shutil
import zipfile
import tarfile
import gzip
import bz2
import lzma
import rarfile
import py7zr
from tqdm import tqdm
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

# Emojis
PACKAGE = '📦'
SUCCESS = '✅'
ERROR = '❌'
STATS = '📊'
CELEBRATE = '🎉'
WAITING = '⏳'

# Colors
GREEN = Fore.GREEN
YELLOW = Fore.YELLOW
RED = Fore.RED
BLUE = Fore.BLUE
CYAN = Fore.CYAN
RESET = Style.RESET_ALL

# Load config
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

# Extract functions
def extract_zip(file_path, extract_to):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

# Similar for others, but for brevity, assume we handle them
def extract_rar(file_path, extract_to):
    with rarfile.RarFile(file_path, 'r') as rar_ref:
        rar_ref.extractall(extract_to)

def extract_7z(file_path, extract_to):
    with py7zr.SevenZipFile(file_path, 'r') as sz_ref:
        sz_ref.extractall(extract_to)

def extract_tar(file_path, extract_to):
    with tarfile.open(file_path, 'r') as tar_ref:
        tar_ref.extractall(extract_to)

# For single file compressions like gz, bz2, xz, need to handle differently
# Assuming they are archives, but gz etc. are usually single files
# For simplicity, skip single file extractions or handle as needed

# Main function
def main():
    config = load_config()
    extrator_config = config.get('extrator_arquivos', {})
    root_folder = extrator_config.get('root_folder', '.')
    log_file = extrator_config.get('log_file', 'extraction_log.txt')

    # Find all compressed files
    compressed_extensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
    compressed_files = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if any(file.lower().endswith(ext) for ext in compressed_extensions):
                compressed_files.append(os.path.join(root, file))

    total_files = len(compressed_files)
    extracted_total = 0
    moved_total = 0
    errors_total = 0

    with tqdm(total=total_files, desc=f'{BLUE}Arquivo{{}} de {total_files}{RESET}', unit='arquivo') as main_pbar:
        for idx, file_path in enumerate(compressed_files, 1):
            main_pbar.set_description(f'{BLUE}Arquivo {idx} de {total_files}{RESET}')
            tqdm.write(f'{PACKAGE} Extraindo: {CYAN}{os.path.basename(file_path)}{RESET}')

            # Determine extract function
            ext = os.path.splitext(file_path)[1].lower()
            extract_func = None
            if ext == '.zip':
                extract_func = extract_zip
            elif ext == '.rar':
                extract_func = extract_rar
            elif ext == '.7z':
                extract_func = extract_7z
            elif ext in ['.tar', '.gz', '.bz2', '.xz']:
                extract_func = extract_tar  # Simplified
            else:
                tqdm.write(f'{ERROR} Tipo não suportado: {file_path}')
                errors_total += 1
                with open(log_file, 'a') as log:
                    log.write(f'Unsupported type: {file_path}\n')
                main_pbar.update(1)
                continue

            # Create temp extract folder
            temp_extract = os.path.join(root_folder, f'temp_extract_{idx}')
            os.makedirs(temp_extract, exist_ok=True)

            try:
                # Extract
                extract_func(file_path, temp_extract)

                # Count files inside
                all_files = []
                for root_dir, dirs, files_in_dir in os.walk(temp_extract):
                    for f in files_in_dir:
                        all_files.append(os.path.join(root_dir, f))

                num_files = len(all_files)
                tqdm.write(f'{STATS} Arquivo contém {YELLOW}{num_files}{RESET} arquivos')

                # Move files to root
                with tqdm(total=num_files, desc=f'{WAITING} Movendo arquivos', leave=False) as sub_pbar:
                    for src_file in all_files:
                        rel_path = os.path.relpath(src_file, temp_extract)
                        dst_file = os.path.join(root_folder, os.path.basename(rel_path))  # Flatten to root
                        # Handle duplicates by renaming
                        counter = 1
                        base, ext_file = os.path.splitext(dst_file)
                        while os.path.exists(dst_file):
                            dst_file = f'{base}_{counter}{ext_file}'
                            counter += 1
                        shutil.move(src_file, dst_file)
                        moved_total += 1
                        sub_pbar.update(1)

                extracted_total += num_files
                tqdm.write(f'{SUCCESS} Extração e movimento concluídos para {os.path.basename(file_path)}')

            except Exception as e:
                tqdm.write(f'{ERROR} Erro ao extrair {file_path}: {str(e)}')
                errors_total += 1
                with open(log_file, 'a') as log:
                    log.write(f'Error extracting {file_path}: {str(e)}\n')

            # Clean temp
            shutil.rmtree(temp_extract, ignore_errors=True)
            main_pbar.update(1)

    # Final summary
    tqdm.write(f'{CELEBRATE} {GREEN}Resumo Final:{RESET}')
    tqdm.write(f'{STATS} Total extraídos: {CYAN}{extracted_total}{RESET}')
    tqdm.write(f'{STATS} Total movidos: {CYAN}{moved_total}{RESET}')
    tqdm.write(f'{ERROR} Total erros: {RED}{errors_total}{RESET}')

if __name__ == '__main__':
    main()