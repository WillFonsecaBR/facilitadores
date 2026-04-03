
import json
import os

from organizador import run_organizador
from separador_de_videos import separar_videos


def carregar_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def menu():
    config = carregar_config()
    while True:
        print('\n=== Menu Principal ===')
        print('1. Organizar Mídias')
        print('2. Separar Vídeos e Imagens')
        print('3. Sair')
        escolha = input('Escolha uma opção: ')
        if escolha == '1':
            # Aqui vai a lógica do organizador_midias, assumindo que já existe
            try:
                run_organizador()
                print('Separação concluída com sucesso.')
            except Exception as e:
                print(f'Erro durante a execução: {e}')
            # Simular execução
            pass
        elif escolha == '2':
            print('Executando separador de vídeos e imagens...')
            try:
                separar_videos()
                print('Separação concluída com sucesso.')
            except Exception as e:
                print(f'Erro durante a separação: {e}')
        elif escolha == '3':
            print('Saindo...')
            break
        else:
            print('Opção inválida. Tente novamente.')

if __name__ == '__main__':
    menu()