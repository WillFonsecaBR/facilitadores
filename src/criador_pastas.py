import os
import json
from tqdm import tqdm

def carregar_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def run_criador_pastas():
    try:
        config = carregar_config()
        # Lê o diretório principal da nova chave no JSON
        root_folder = config.get('criador_pastas', {}).get('root_folder')
        
        if not root_folder or not os.path.exists(root_folder):
            print(f"Erro: Diretório principal '{root_folder}' não encontrado no config.json ou não existe.")
            return

        pastas_alvo = ["00 - FINALIZADOS", "00 - COM MD"]
        dirs_to_process = []

        print(f"Mapeando diretórios em: {root_folder}...")
        
        # Coleta todos os diretórios primeiro
        for root, dirs, files in os.walk(root_folder):
            # Remove as pastas alvo da lista 'dirs' para que o os.walk não entre nelas
            # Isso evita a criação infinita de subpastas dentro das subpastas recém-criadas
            for pasta in pastas_alvo:
                if pasta in dirs:
                    dirs.remove(pasta)
            
            dirs_to_process.append(root)

        # Cria as pastas com a barra de progresso do tqdm
        for d in tqdm(dirs_to_process, desc="Verificando/Criando pastas", unit="dir"):
            for pasta in pastas_alvo:
                caminho_completo = os.path.join(d, pasta)
                
                # Verifica explicitamente se a pasta já existe antes de criar
                # Se já existir, ela é ignorada e os arquivos dentro são preservados
                if not os.path.exists(caminho_completo):
                    os.makedirs(caminho_completo)
                
    except Exception as e:
        print(f"Ocorreu um erro ao criar as pastas: {e}")

if __name__ == '__main__':
    run_criador_pastas()