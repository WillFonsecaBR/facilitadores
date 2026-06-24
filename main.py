import json
import os
from organizador import run_organizador
from separador_de_videos import separar_videos
from selecionador import run_selecionador
from criador_pastas import run_criador_pastas
from organizador_videos_edicao import run_organizador_videos
from movendo_videos_marca_dagua import run_movendo_videos_marca_dagua

def carregar_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def menu():
    while True:
        print('\n=== Menu Principal ===')
        print('1. Organizar Mídias')
        print('2. Separar de Vídeos')
        print('3. Selecionador de Imagens')
        print('4. Criador de Subpastas (Finalizados/MD)')
        print('5. Organizador de Vídeos para Edição')
        print('6. Mover Vídeos com Marca D\'Água')
        print('7. Sair')

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
                print('Iniciando Selecionador de Imagens...')
                run_selecionador()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '4':
            try:
                print('Iniciando Criador de Pastas...')
                run_criador_pastas()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '5':
            try:
                print('Iniciando Organizador de Vídeos para Edição...')
                run_organizador_videos()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '6':
            try:
                print('Iniciando Movimentação de Vídeos com Marca D\'Água...')
                run_movendo_videos_marca_dagua()
                print('\nProcesso finalizado.')
            except Exception as e:
                print(f'Erro: {e}')

        elif escolha == '7':
            print('Saindo...')
            break
        else:
            print('Opção inválida.')

if __name__ == '__main__':
    menu()