import json
import os
from src.organizador import run_organizador
from src.separador_de_videos import run_separar_videos
from src.selecionador import run_selecionador
from src.criador_pastas import run_criador_pastas
from src.organizador_videos_edicao import run_organizador_videos
from src.movendo_videos_marca_dagua import run_movendo_videos_marca_dagua
from src.extrator_arquivos import main as run_extrator
from src.limpeza_de_urls import run_limpeza_de_urls
from src.video_pack_creator import run_video_pack_creator

def load_config():
    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'config.json'
    )
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    config = load_config()
    while True:
        print('\n===== MENU PRINCIPAL =====')
        print('1. Organizar Mídias')
        print('2. Separar Vídeos')
        print('3. Extrair Arquivos')
        print('4. Selecionar Imagens')
        print('5. Criar Pastas')
        print('6. Organizar Vídeos para Edição')
        print('7. Mover Vídeos com Marca D\'água')
        print('8. Renomear Arquivos')
        print('9. Criar Packs de Vídeos')
        print('10. Sair')
        escolha = input('\nEscolha uma opção: ')

        if escolha == '1':
            try:
                print('Iniciando Organizador de Mídias...')
                run_organizador()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '2':
            try:
                print('Iniciando Separador de Vídeos...')
                run_separar_videos()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '3':
            try:
                print('Iniciando Extrator de Arquivos...')
                run_extrator()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '4':
            try:
                print('Iniciando Selecionador de Imagens...')
                run_selecionador()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '5':
            try:
                print('Iniciando Criador de Pastas...')
                run_criador_pastas()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '6':
            try:
                print('Iniciando Organizador de Vídeos para Edição...')
                run_organizador_videos()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '7':
            try:
                print('Iniciando Movimentação de Vídeos com Marca D\'água...')
                run_movendo_videos_marca_dagua()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '8':
            try:
                print('Iniciando Renomeador de Arquivos...')
                run_renomeador_arquivos()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '9':
            try:
                print('Iniciando Criador de Packs de Vídeos...')
                run_video_pack_creator()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '10':
            print('Saindo...')
            break

        else:
            print('Opção inválida. Tente novamente.')

if __name__ == '__main__':
    main()