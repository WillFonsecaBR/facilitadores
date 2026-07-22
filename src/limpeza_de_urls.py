"""
Módulo de Limpeza de URLs de Redes Sociais.

Este módulo é responsável por limpar URLs de vídeos do TikTok, YouTube e Instagram,
removendo parâmetros de rastreamento (tudo a partir do caractere '?'), removendo
URLs duplicadas, comparando com arquivos de database existentes por plataforma e
gerando arquivos de comparação e relatórios auxiliares.

Estrutura de pastas esperada (relativa à raiz do projeto):
    - database_links/database/TIKTOK/*.yaml
    - database_links/database/INSTAGRAM/*.yaml
    - database_links/database/YOUTUBE/*.yaml
    - database_links/para_limpar/<nicho>.yaml   (arquivo de entrada único)
    - logs/    (log de atividades)
    - error/   (log de erros)

Função principal exposta: run_limpeza_de_urls()
"""

import os
import re
import glob
import logging
from datetime import datetime

import yaml
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constantes e configurações globais
# ---------------------------------------------------------------------------

# Ordem canônica dos emojis usados nos arquivos de database
EMOJIS_ORDEM = ['❌', '✅', '﹖', '？', '☑️']

# Caminhos base relativos à raiz do projeto
PASTA_DATABASE = 'database_links/database'
PASTA_PARA_LIMPAR = 'database_links/para_limpar'
PASTA_LOGS = 'logs'
PASTA_ERROR = 'error'

# Plataformas suportadas
PLATAFORMAS = ['TIKTOK', 'INSTAGRAM', 'YOUTUBE']

# Arquivos gerados pelo módulo que não devem ser considerados como entrada
ARQUIVOS_GERADOS = {'duplicados.yaml', 'urls_puras.yaml', 'urls_com_texto.yaml'}

# Loggers globais (configurados por configurar_logging)
logger_atividades = None
logger_erros = None


# ---------------------------------------------------------------------------
# Funções auxiliares internas
# ---------------------------------------------------------------------------

def _extrair_emoji(linha):
    """Extrai o primeiro emoji reconhecido da linha, ou None se não houver."""
    for emoji in EMOJIS_ORDEM:
        if emoji in linha:
            return emoji
    return None


def _e_arquivo_gerado(nome_arquivo):
    """Verifica se o arquivo é um dos arquivos gerados pelo próprio módulo."""
    if nome_arquivo in ARQUIVOS_GERADOS:
        return True
    if nome_arquivo.startswith('comparacao_'):
        return True
    return False


# ---------------------------------------------------------------------------
# Funções principais do módulo
# ---------------------------------------------------------------------------

def configurar_logging():
    """Configura os loggers de atividades e de erros com arquivos datados."""
    global logger_atividades, logger_erros

    os.makedirs(PASTA_LOGS, exist_ok=True)
    os.makedirs(PASTA_ERROR, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Logger de atividades
    logger_atividades = logging.getLogger('limpeza_de_urls_atividades')
    logger_atividades.setLevel(logging.INFO)
    logger_atividades.handlers.clear()
    handler_ativ = logging.FileHandler(
        os.path.join(PASTA_LOGS, f'limpeza_de_urls_{timestamp}.log'),
        encoding='utf-8'
    )
    handler_ativ.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    logger_atividades.addHandler(handler_ativ)

    # Logger de erros
    logger_erros = logging.getLogger('limpeza_de_urls_erros')
    logger_erros.setLevel(logging.ERROR)
    logger_erros.handlers.clear()
    handler_erro = logging.FileHandler(
        os.path.join(PASTA_ERROR, f'limpeza_de_urls_erro_{timestamp}.log'),
        encoding='utf-8'
    )
    handler_erro.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    logger_erros.addHandler(handler_erro)


def localizar_arquivo_para_limpar(pasta_para_limpar):
    """Localiza o único arquivo .yaml de entrada dentro da pasta para_limpar."""
    arquivos = glob.glob(os.path.join(pasta_para_limpar, '*.yaml'))
    # Filtrar arquivos gerados pelo próprio módulo
    arquivos = [
        a for a in arquivos
        if not _e_arquivo_gerado(os.path.basename(a))
    ]
    if len(arquivos) != 1:
        msg = (
            f'Esperado exatamente 1 arquivo .yaml em {pasta_para_limpar}, '
            f'encontrado(s) {len(arquivos)}.'
        )
        if logger_erros:
            logger_erros.error(msg)
        raise ValueError(msg)
    return arquivos[0]


def localizar_arquivo_database_correspondente(nome_arquivo, pasta_database):
    """Procura nas subpastas TIKTOK, INSTAGRAM e YOUTUBE arquivos com o mesmo nome."""
    correspondencias = {}
    for plataforma in PLATAFORMAS:
        caminho_subpasta = os.path.join(pasta_database, plataforma)
        if not os.path.isdir(caminho_subpasta):
            continue
        candidatos = glob.glob(os.path.join(caminho_subpasta, nome_arquivo))
        if candidatos:
            correspondencias[plataforma] = candidatos[0]
    if not correspondencias:
        msg = f'Nenhuma correspondência encontrada no database para o arquivo: {nome_arquivo}'
        if logger_erros:
            logger_erros.error(msg)
        print(f'Erro: {msg}')
        return None
    return correspondencias


def identificar_plataforma(url):
    """Identifica a plataforma da URL com base no domínio."""
    if not url:
        return None
    url_lower = url.lower()
    if 'tiktok.com' in url_lower:
        return 'TIKTOK'
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'YOUTUBE'
    if 'instagram.com' in url_lower:
        return 'INSTAGRAM'
    return None


def limpar_url(url):
    """Remove tudo a partir do caractere '?' (inclusive), preservando domínio e usuário."""
    if not url:
        return url
    indice = url.find('?')
    if indice != -1:
        return url[:indice]
    return url


def extrair_url_pura(linha):
    """Extrai somente a URL (http/https) contida na linha, preservando o restante."""
    if not linha:
        return None
    match = re.search(r'https?://[^\s\'"]+', linha)
    if match:
        url = match.group(0).rstrip('\'",')
        return url
    return None


def separar_urls_com_texto_antes(linhas):
    """Separa linhas em: (a) apenas URL e (b) linhas com texto/rótulo antes da URL."""
    apenas_urls = []
    com_texto = []
    for linha in linhas:
        linha_stripped = linha.strip()
        # Remover marcador de lista YAML ("- ") se presente, para classificação
        if linha_stripped.startswith('- '):
            linha_sem_marcador = linha_stripped[2:]
        else:
            linha_sem_marcador = linha_stripped
        match = re.search(r'https?://[^\s]+', linha_sem_marcador)
        if not match:
            continue
        inicio_url = match.start()
        texto_antes = linha_sem_marcador[:inicio_url].strip()
        if texto_antes == '':
            apenas_urls.append(linha)
        else:
            com_texto.append(linha)
    return apenas_urls, com_texto


def remover_duplicados(lista_urls):
    """Remove URLs duplicadas preservando a ordem e mantendo a primeira ocorrência."""
    vistas = set()
    sem_duplicados = []
    duplicados = []
    for url in lista_urls:
        if url in vistas:
            duplicados.append(url)
        else:
            vistas.add(url)
            sem_duplicados.append(url)
    return sem_duplicados, duplicados


def salvar_duplicados(duplicados, pasta_para_limpar):
    """Salva a lista de URLs duplicadas em duplicados.yaml dentro de para_limpar."""
    caminho = os.path.join(pasta_para_limpar, 'duplicados.yaml')
    with open(caminho, 'w', encoding='utf-8') as f:
        yaml.safe_dump(duplicados, f, allow_unicode=True, default_flow_style=False)


def arquivo_emojis_estao_misturados(linhas_com_emoji):
    """Verifica se as linhas estão agrupadas por emoji (False) ou misturadas (True)."""
    emojis_encontrados = []
    for linha in linhas_com_emoji:
        emoji = _extrair_emoji(linha)
        if emoji:
            emojis_encontrados.append(emoji)
    if not emojis_encontrados:
        return False
    # Verificar se a sequência de emojis está em ordem não-decrescente
    # segundo a ordem canônica (o que indica que estão agrupados)
    indices = [EMOJIS_ORDEM.index(e) for e in emojis_encontrados if e in EMOJIS_ORDEM]
    for i in range(1, len(indices)):
        if indices[i] < indices[i - 1]:
            return True
    return False


def reorganizar_por_emoji(linhas_com_emoji):
    """Reagrupa as linhas por emoji na ordem canônica, sem alterar o conteúdo."""
    grupos = {emoji: [] for emoji in EMOJIS_ORDEM}
    sem_emoji = []
    for linha in linhas_com_emoji:
        emoji = _extrair_emoji(linha)
        if emoji and emoji in grupos:
            grupos[emoji].append(linha)
        else:
            sem_emoji.append(linha)
    reorganizadas = []
    for emoji in EMOJIS_ORDEM:
        reorganizadas.extend(grupos[emoji])
    reorganizadas.extend(sem_emoji)
    return reorganizadas


def carregar_urls_puras_do_database(caminho_arquivo_database):
    """Lê o arquivo de database e retorna {url_pura: linha_original_completa}."""
    dicionario = {}
    if not os.path.isfile(caminho_arquivo_database):
        return dicionario
    with open(caminho_arquivo_database, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
    for linha in linhas:
        linha = linha.rstrip('\n').rstrip('\r')
        if not linha.strip():
            continue
        url = extrair_url_pura(linha)
        if url:
            url_limpa = limpar_url(url)
            if url_limpa not in dicionario:
                dicionario[url_limpa] = linha
    return dicionario


def comparar_e_gerar_arquivo_comparacao(urls_novas_limpas, dicionario_database, plataforma, pasta_para_limpar):
    """Compara URLs novas com o database e gera arquivo de comparação tabulado."""
    caminho_saida = os.path.join(pasta_para_limpar, f'comparacao_{plataforma}.yaml')
    with open(caminho_saida, 'w', encoding='utf-8') as f:
        for url in tqdm(urls_novas_limpas, desc='Comparando URLs', unit='url'):
            if url in dicionario_database:
                linha_db = dicionario_database[url]
                f.write(f'{linha_db}\t{url}\n')
            else:
                f.write(f'NÃO ENCONTRADO NO DATABASE\t{url}\n')
    if logger_atividades:
        logger_atividades.info(f'Arquivo de comparação gerado: {caminho_saida}')


def processar_arquivo_para_limpar(nome_arquivo):
    """Função orquestradora que executa todas as etapas de limpeza na ordem correta."""
    try:
        if logger_atividades:
            logger_atividades.info(f'Iniciando processamento do arquivo: {nome_arquivo}')

        # Etapa 1: Localizar correspondências no database
        correspondencias = localizar_arquivo_database_correspondente(nome_arquivo, PASTA_DATABASE)
        if correspondencias is None:
            return None

        if logger_atividades:
            logger_atividades.info(f'Correspondências encontradas: {list(correspondencias.keys())}')

        # Etapa 2: Ler linhas do arquivo para_limpar
        caminho_para_limpar = os.path.join(PASTA_PARA_LIMPAR, nome_arquivo)
        with open(caminho_para_limpar, 'r', encoding='utf-8') as f:
            linhas_originais = f.readlines()
        linhas_originais = [l.rstrip('\n').rstrip('\r') for l in linhas_originais]

        # Etapa 3: Extrair URLs puras de cada linha
        urls_extraidas = []
        for linha in linhas_originais:
            url = extrair_url_pura(linha)
            if url:
                urls_extraidas.append(url)

        if logger_atividades:
            logger_atividades.info(f'Total de URLs extraídas: {len(urls_extraidas)}')

        # Etapa 4: Limpar URLs (remover parâmetros após '?') com barra de progresso
        urls_limpas = []
        for url in tqdm(urls_extraidas, desc='Limpando URLs', unit='url'):
            urls_limpas.append(limpar_url(url))

        if logger_atividades:
            logger_atividades.info(f'Total de URLs após limpeza: {len(urls_limpas)}')

        # Etapa 5: Remover duplicados e salvar duplicados.yaml
        urls_sem_duplicados, duplicados = remover_duplicados(urls_limpas)
        salvar_duplicados(duplicados, PASTA_PARA_LIMPAR)

        if logger_atividades:
            logger_atividades.info(f'URLs duplicadas removidas: {len(duplicados)}')
            logger_atividades.info(f'URLs únicas: {len(urls_sem_duplicados)}')

        # Etapa 6: Para cada plataforma correspondente, verificar/reorganizar emojis
        # do database (em memória, sem alterar o arquivo) e comparar
        for plataforma, caminho_db in correspondencias.items():
            with open(caminho_db, 'r', encoding='utf-8') as f:
                linhas_db = f.readlines()
            linhas_db = [l.rstrip('\n').rstrip('\r') for l in linhas_db]

            # Verificar se emojis estão misturados e reorganizar em memória
            if arquivo_emojis_estao_misturados(linhas_db):
                if logger_atividades:
                    logger_atividades.info(
                        f'Emojis misturados detectados no database de {plataforma}. '
                        f'Reorganizando em memória (sem alterar o arquivo original).'
                    )
                linhas_db = reorganizar_por_emoji(linhas_db)

            # Carregar dicionário de URLs puras do database
            dicionario_db = {}
            for linha in linhas_db:
                if not linha.strip():
                    continue
                url_db = extrair_url_pura(linha)
                if url_db:
                    url_db_limpa = limpar_url(url_db)
                    if url_db_limpa not in dicionario_db:
                        dicionario_db[url_db_limpa] = linha

            # Etapa 7: Comparar e gerar arquivo de comparação
            comparar_e_gerar_arquivo_comparacao(
                urls_sem_duplicados, dicionario_db, plataforma, PASTA_PARA_LIMPAR
            )

        # Etapa 8: Reescrever o arquivo para_limpar com URLs limpas (preservando emojis/texto)
        linhas_processadas = []
        for linha in linhas_originais:
            url = extrair_url_pura(linha)
            if url:
                url_limpa = limpar_url(url)
                linha_processada = linha.replace(url, url_limpa)
                linhas_processadas.append(linha_processada)
            else:
                linhas_processadas.append(linha)

        # Remover duplicados das linhas processadas (baseado na URL limpa)
        urls_vistas = set()
        linhas_sem_duplicados = []
        for linha in linhas_processadas:
            url = extrair_url_pura(linha)
            if url:
                url_limpa = limpar_url(url)
                if url_limpa in urls_vistas:
                    continue
                urls_vistas.add(url_limpa)
            linhas_sem_duplicados.append(linha)

        # Salvar arquivo limpo de volta
        with open(caminho_para_limpar, 'w', encoding='utf-8') as f:
            for linha in linhas_sem_duplicados:
                f.write(linha + '\n')

        # Etapa 9: Separar URLs com texto antes e URLs puras
        apenas_urls, com_texto = separar_urls_com_texto_antes(linhas_sem_duplicados)

        caminho_apenas_urls = os.path.join(PASTA_PARA_LIMPAR, 'urls_puras.yaml')
        caminho_com_texto = os.path.join(PASTA_PARA_LIMPAR, 'urls_com_texto.yaml')

        with open(caminho_apenas_urls, 'w', encoding='utf-8') as f:
            for linha in apenas_urls:
                f.write(linha + '\n')

        with open(caminho_com_texto, 'w', encoding='utf-8') as f:
            for linha in com_texto:
                f.write(linha + '\n')

        if logger_atividades:
            logger_atividades.info(f'URLs puras (sem texto antes): {len(apenas_urls)}')
            logger_atividades.info(f'URLs com texto antes: {len(com_texto)}')
            logger_atividades.info('Processamento concluído com sucesso.')

        print('\nLimpeza de URLs concluída com sucesso!')
        print(f'  - URLs únicas: {len(urls_sem_duplicados)}')
        print(f'  - Duplicados removidos: {len(duplicados)}')
        print(f'  - Arquivos gerados em: {PASTA_PARA_LIMPAR}')

    except Exception as e:
        if logger_erros:
            logger_erros.error(f'Erro durante processamento: {e}', exc_info=True)
        print(f'Erro durante o processamento: {e}')
        return None


def run_limpeza_de_urls():
    """Função de entrada pública para o módulo de limpeza de URLs."""
    try:
        print('Iniciando Limpeza de URLs de Vídeos (TikTok/YouTube/Instagram)...')
        configurar_logging()
        if logger_atividades:
            logger_atividades.info('=== Iniciando Limpeza de URLs ===')

        caminho_arquivo = localizar_arquivo_para_limpar(PASTA_PARA_LIMPAR)
        nome_arquivo = os.path.basename(caminho_arquivo)

        if logger_atividades:
            logger_atividades.info(f'Arquivo para limpar localizado: {nome_arquivo}')

        processar_arquivo_para_limpar(nome_arquivo)

    except Exception as e:
        if logger_erros:
            logger_erros.error(f'Erro em run_limpeza_de_urls: {e}', exc_info=True)
        print(f'Erro: {e}')