import json
import os
from src.organizador import run_organizador
from src.separador_de_videos import separar_videos
from src.selecionador import run_selecionador
from src.criador_pastas import run_criador_pastas
from src.organizador_videos_edicao import run_organizador_videos
from src.movendo_videos_marca_dagua import run_movendo_videos_marca_dagua
from src.extrator_arquivos import main as run_extrator

def carregar_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def menu():
    while True:
        print('\n=== Menu Principal ===')
        print('1. Organizar Mídias')
        print('2. Separar de Vídeos')
        print('3. Extrator de Arquivos Compactados') 
        print('4. Selecionador de Imagens')            
        print('5. Criador de Subpastas (Finalizados/MD)') 
        print('6. Organizador de Vídeos para Edição')      
        print('7. Mover Vídeos com Marca D\'Água')         
        print('8. Sair')                                   

        escolha = input('Escolha uma opção: ')

        if escolha == '1':
            try:
                run_organizador()
                print('Organização concluída.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '2':
            try:
                separar_videos()
                print('Separação concluída.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '3':
            try:
                print('Iniciando Extrator de Arquivos Compactados...')
                run_extrator()
                print('\nExtração concluída.')
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
                print('Iniciando Movimentação de Vídeos com Marca D\'Água...')
                run_movendo_videos_marca_dagua()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '8':
            print('Saindo...')
            break

        else:
            print('Opção inválida.')

if __name__ == '__main__':
    menu()