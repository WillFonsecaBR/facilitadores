import os
import json
import shutil
from pathlib import Path
from tqdm import tqdm

def carregar_configuracao():
    """Carrega as configurações do arquivo config.json."""
    config_path = Path('config.json')
    if not config_path.exists():
        raise FileNotFoundError("Arquivo 'config.json' não encontrado.")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    if 'movendo_videos_marca_dagua' not in config:
        raise KeyError("Chave 'movendo_videos_marca_dagua' não encontrada no config.json.")
    
    return config['movendo_videos_marca_dagua']

def obter_nome_unico(destino_arquivo):
    """Gera um nome de arquivo único se houver conflito no destino."""
    if not destino_arquivo.exists():
        return destino_arquivo
    
    nome = destino_arquivo.stem
    ext = destino_arquivo.suffix
    diretorio = destino_arquivo.parent
    contador = 1
    
    while True:
        novo_nome = f"{nome}_{contador}{ext}"
        novo_destino = diretorio / novo_nome
        if not novo_destino.exists():
            return novo_destino
        contador += 1

def run_movendo_videos_marca_dagua():
    """Função principal para organizar vídeos com marca d'água."""
    try:
        config = carregar_configuracao()
        root_path = Path(config.get('root_folder', ''))

        if not root_path.exists() or not root_path.is_dir():
            print(f"Erro: O diretório raiz '{root_path}' não existe.")
            return

        # Pasta principal de destino na raiz
        nome_pasta_md = "00 - COM MD"
        pasta_destino_raiz = root_path / nome_pasta_md
        
        if not pasta_destino_raiz.exists():
            pasta_destino_raiz.mkdir(parents=True)

        extensoes_video = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.wmv', '.flv', '.webm', '.mpeg', '.mpg'}

        # FASE 1: Coleta de arquivos e pastas
        print("\nColetando informações dos arquivos...")
        tarefas_movimentacao = []
        pastas_para_limpar = set()

        # Listar subpastas de primeiro nível (ex: ANIMAIS, COMIDAS)
        subpastas_nivel_1 = [d for d in root_path.iterdir() if d.is_dir() and d.name != nome_pasta_md]

        for pasta_topo in subpastas_nivel_1:
            # Procurar recursivamente por pastas chamadas exatamente "00 - COM MD"
            for pasta_alvo in pasta_topo.rglob(nome_pasta_md):
                # Ignorar a pasta de destino principal se ela for encontrada por algum motivo
                if pasta_alvo.resolve() == pasta_destino_raiz.resolve():
                    continue

                # Listar vídeos DIRETAMENTE dentro desta pasta
                arquivos_na_pasta = [f for f in pasta_alvo.iterdir() if f.is_file() and f.suffix.lower() in extensoes_video]
                
                if arquivos_na_pasta:
                    # O destino final é root/00 - COM MD/NOME_DA_PASTA_TOPO/
                    diretorio_final_agrupado = pasta_destino_raiz / pasta_topo.name
                    
                    for video in arquivos_na_pasta:
                        tarefas_movimentacao.append((video, diretorio_final_agrupado))
                    
                    pastas_para_limpar.add(pasta_alvo)

        if not tarefas_movimentacao:
            print("Nenhum vídeo encontrado para mover.")
            return

        # FASE 2: Movimentação com barra de progresso
        videos_movidos = 0
        
        with tqdm(total=len(tarefas_movimentacao), desc="Organizando mídias", unit="arquivo", 
                  bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
            
            for origem, dir_destino in tarefas_movimentacao:
                if not dir_destino.exists():
                    dir_destino.mkdir(parents=True, exist_ok=True)
                
                destino_final = obter_nome_unico(dir_destino / origem.name)
                
                try:
                    shutil.move(str(origem), str(destino_final))
                    videos_movidos += 1
                except Exception as e:
                    print(f"\nErro ao mover {origem.name}: {e}")
                
                pbar.update(1)

        # FASE 3: Limpeza de pastas vazias
        pastas_removidas = 0
        for pasta in pastas_para_limpar:
            try:
                # Verifica se a pasta está vazia (ignora arquivos ocultos como .DS_Store se necessário)
                conteudo = [f for f in pasta.iterdir() if f.name != '.DS_Store']
                if not conteudo:
                    pasta.rmdir()
                    pastas_removidas += 1
            except Exception:
                pass

        # Resumo Final
        print("\n" + "="*30)
        print("RESUMO DO PROCESSO")
        print(f"Vídeos movidos: {videos_movidos}")
        print(f"Pastas '{nome_pasta_md}' removidas (vazias): {pastas_removidas}")
        print("="*30 + "\n")

    except Exception as e:
        print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    run_movendo_videos_marca_dagua()