# Este script le o arquivo config.json localizado no mesmo diretorio deste script.
# A partir do config.json, obtem a pasta raiz por meio da chave criador_pastas.root_folder.
# Em seguida, percorre todos os diretorios existentes dentro da pasta raiz informada.
# Durante o percurso, evita entrar nas pastas alvo ("00 - FINALIZADOS" e "00 - COM MD")
# para nao criar subpastas infinitamente dentro delas.
# Para cada diretorio encontrado, garante a existencia das pastas "00 - FINALIZADOS"
# e "00 - COM MD", criando-as apenas se ainda nao existirem.
# Registra informacoes de execucao na pasta logs, por meio de arquivo de log.
# Em caso de excecao, registra os erros na pasta ERROR, gravando detalhes do ocorrido.
import os
import json
import logging
from tqdm import tqdm

# Configuração de logs
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(logs_dir, 'criador_pastas.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def carregar_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_criador_pastas():
    try:
        config = carregar_config()
        # Lê o diretório principal da nova chave no JSON
        root_folder = config.get('criador_pastas', {}).get('root_folder')
        
        if not root_folder or not os.path.exists(root_folder):
            print(f"Erro: Diretório principal '{root_folder}' não encontrado no config.json ou não existe.")
            logging.error(f"Diretório principal '{root_folder}' não encontrado no config.json ou não existe.")
            return

        pastas_alvo = ["00 - FINALIZADOS", "00 - COM MD"]
        dirs_to_process = []

        print(f"Mapeando diretórios em: {root_folder}...")
        logging.info(f"Mapeando diretórios em: {root_folder}...")
        
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
                    logging.info(f"Criada pasta: {caminho_completo}")
                
    except Exception as e:
        print(f"Ocorreu um erro ao criar as pastas: {e}")
        logging.error(f"Ocorreu um erro ao criar as pastas: {e}")
        error_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ERROR')
        os.makedirs(error_dir, exist_ok=True)
        with open(os.path.join(error_dir, 'erro_criador_pastas.txt'), 'a', encoding='utf-8') as f:
            f.write(f"{e}\n")

if __name__ == '__main__':
    run_criador_pastas()