import os
import sys

import customtkinter as ctk

from src.compactador_packs import CompactadorPacksFrame
from src.conferencia_videos import ConferenciaVideosFrame
from src.copiador_produtos import CopiadorProdutosFrame
from src.criador_de_packs import CriadorPacksFrame
from src.exclusao_massiva import ExclusaoMassivaFrame
from src.extrair_arquivos import ExtrairArquivosFrame
from src.limpador_urls import LimpadorUrlsFrame
from src.movimentar_videos import MovimentarVideosFrame
from src.organizador_conferencia import OrganizadorConferenciaFrame
from src.rastreador_links import RastreadorLinksFrame
from src.renomeador_de_packs import RenomeadorPacksFrame
# Importação dos frames de cada ferramenta
from src.renomeador_de_videos import RenomeadorFrame
from src.transferidor import FileTransferFrame


class AppFacilitadores(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FACILITADORES | Suite de Automação")
        self.geometry("1200x800")
        
        # Cores Padrão Dashboard Pro
        self.bg_color = "#0f0f0f"
        self.card_color = "#1a1a1a"
        self.accent_color = "#3498db"
        self.hover_color = "#2980b9"
        
        ctk.set_appearance_mode("dark")
        
        # Arquivo para persistência do histórico de abertura
        self.recents_file = "recents.txt"
        self.recents = self.load_recents()
        
        # Layout Grid Principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#141414")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        self.logo = ctk.CTkLabel(self.sidebar, text="FACILITADORES", 
                                font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
                                text_color=self.accent_color)
        self.logo.grid(row=0, column=0, padx=20, pady=(40, 50))

        self.btn_menu = ctk.CTkButton(self.sidebar, text="  🏠  Dashboard", 
                                     anchor="w", height=45, corner_radius=8,
                                     fg_color=self.accent_color, font=("Segoe UI", 13, "bold"),
                                     command=self.show_main_menu)
        self.btn_menu.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.btn_sair = ctk.CTkButton(self.sidebar, text="  🚪  Sair", 
                                     anchor="w", height=45, corner_radius=8,
                                     fg_color="transparent", border_width=1, border_color="#333",
                                     hover_color="#e74c3c", font=("Segoe UI", 13),
                                     command=self.quit)
        self.btn_sair.grid(row=11, column=0, padx=20, pady=20, sticky="ew")

        # --- ÁREA CENTRAL ---
        self.main_container = ctk.CTkFrame(self, corner_radius=20, fg_color=self.bg_color)
        self.main_container.grid(row=0, column=1, padx=25, pady=25, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.show_main_menu()

    def load_recents(self):
        """Carrega a lista de programas abertos recentemente do arquivo local."""
        if os.path.exists(self.recents_file):
            try:
                with open(self.recents_file, "r", encoding="utf-8") as f:
                    return [line.strip() for line in f if line.strip()]
            except:
                pass
        return []

    def save_recents(self):
        """Salva a lista actualizada de programas recentemente abertos."""
        try:
            with open(self.recents_file, "w", encoding="utf-8") as f:
                for item in self.recents:
                    f.write(f"{item}\n")
        except:
            pass

    def registrar_abertura(self, id_op):
        """Move o programa aberto para o topo da lista de recentes."""
        if id_op in self.recents:
            self.recents.remove(id_op)
        self.recents.insert(0, id_op)
        self.save_recents()

    def clear_container(self):
        """Limpa a tela central para carregar um novo módulo."""
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def render_top_bar(self):
        """Renderiza a barra superior com botão de voltar."""
        top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=10)
        btn_voltar = ctk.CTkButton(top_bar, text="← Voltar ao Dashboard", width=150, 
                                   fg_color="transparent", border_width=1, border_color="#333",
                                   command=self.show_main_menu)
        btn_voltar.pack(side="left")

    def show_main_menu(self):
        """Exibe o Dashboard principal com os cards das ferramentas ordenados por uso recente."""
        self.clear_container()
        
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.pack(fill="x", padx=30, pady=(30, 20))
        
        ctk.CTkLabel(header_frame, text="Minhas Ferramentas", 
                     font=ctk.CTkFont(size=26, weight="bold")).pack(side="left")

        menu_scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        menu_scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # Definição padrão das ferramentas no menu (TODOS OS TÍTULOS EM UPPERCASE)
        opcoes = [
            ("❌ EXCLUSÃO MASSIVA", "exclusao_massiva", "Exclusão ultra rápida e definitiva de arquivos e pastas em massa (CUIDADO!)"),
            ("COPIADOR DE PRODUTOS", "copiador_produtos", "Copia aleatoriamente 20 vídeos de cada pack para a pasta de produtos organizada por nicho"),
            ("COMPACTADOR DE PACKS", "compactador_packs", "Compacta e criptografa pastas de packs em formato TAR.GZ com senhas de 30 caracteres"),
            ("ORGANIZADOR DE CONFERÊNCIA", "organizador_conferencia", "Organiza vídeos ou imagens da raiz em pastas dedicadas com subpastas internas"),
            ("RENOMEADOR DE PACKS", "renomeador_packs", "Renomeia pastas principais e subpastas movendo imagens para 00 - IMAGENS"),
            ("CRIAR PACKS DE VÍDEOS", "criador_packs", "Organiza lotes de vídeos em pastas de packs com extração automática de frames"),
            ("RASTREADOR DE LINKS", "rastreador", "Coleta links e tamanhos de arquivos de sites para cálculo de volumetria"),
            ("CONFERÊNCIA DE VÍDEOS", "conferencia", "Extração de frames e separação automática de vídeos com marca d'água"),
            ("LIMPADOR DE URLS 2.0", "limpador", "Higienização de links do Instagram com auditoria de banco de dados"),
            ("MOVIMENTAR VÍDEOS", "movimentar", "Move vídeos das subpastas para a raiz e imagens para 00_IMAGENS"),
            ("RENOMEADOR DE VÍDEOS", "renomeador", "Embaralhamento aleatório e organização profissional de alta escala"),
            ("TRANSFERIDOR & AUDITOR", "transferidor", "Sincronize e valide a integridade dos seus arquivos"),
            ("EXTRAIR ARQUIVOS", "extrair", "Extração em massa de arquivos compactados"),
            ("SELECIONAR IMAGENS", "imagens", "Curadoria rápida e seleção de fotos"),
            ("CRIAR PASTAS", "pastas", "Estruturação automatizada de diretórios"),
            ("MARCA D'ÁGUA", "watermark", "Processamento e aplicação de marca d'água em vídeos"),
        ]

        # Algoritmo de Ordenação Dinâmica (MRU - Most Recently Used)
        posicao_recentes = {id_op: idx for idx, id_op in enumerate(self.recents)}
        
        def sort_key(item):
            id_op = item[1]
            if id_op in posicao_recentes:
                return (0, posicao_recentes[id_op])  # Prioridade 0: Aparece no topo na ordem do arquivo
            return (1, opcoes.index(item))           # Prioridade 1: Mantém a ordem original abaixo

        opcoes_ordenadas = sorted(opcoes, key=sort_key)

        for nome, id_op, desc in opcoes_ordenadas:
            # Lógica de destaque visual do último programa utilizado
            is_last_used = (len(self.recents) > 0 and id_op == self.recents[0])
            
            # Definição de cores dinâmicas para os cards e botões de acordo com o uso
            if id_op == "exclusao_massiva":
                # Tema Vermelho de Perigo Permanente (Sempre Vermelho!)
                card_bg = "#240a0a"  # Tom vermelho escuro sutil
                border_color = "#e74c3c"
                border_width = 2
                title_color = "#e74c3c"
                btn_fg = "#e74c3c"
                btn_hover = "#c0392b"
                btn_text_color = "white"
            elif is_last_used:
                # Tema Amarelo (Último Utilizado)
                card_bg = "#221f10"  # Tom dourado/amarelo escuro sutil
                border_color = "#f1c40f"
                border_width = 2
                title_color = "#f1c40f"
                btn_fg = "#f1c40f"
                btn_hover = "#d4ac0d"
                btn_text_color = "#0f0f0f"  # Texto escuro para contraste no botão amarelo
            else:
                # Tema Azul (Não Utilizados)
                card_bg = "#0a1424"  # Tom azul escuro sutil
                border_color = "#3498db"
                border_width = 2
                title_color = "white"
                btn_fg = "#3498db"
                btn_hover = "#2980b9"
                btn_text_color = "white"

            item_frame = ctk.CTkFrame(menu_scroll, height=85, corner_radius=12, 
                                      fg_color=card_bg, border_color=border_color, border_width=border_width)
            item_frame.pack(fill="x", padx=10, pady=6)
            item_frame.pack_propagate(False)

            info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(side="left", padx=25, fill="y")
            
            ctk.CTkLabel(info_frame, text=nome, font=ctk.CTkFont(size=16, weight="bold"), 
                         text_color=title_color).pack(pady=(18, 2), anchor="w")
            
            ctk.CTkLabel(info_frame, text=desc, font=ctk.CTkFont(size=12), 
                         text_color="#777").pack(anchor="w")

            # Lógica de roteamento
            if id_op == "exclusao_massiva":
                cmd_original = self.abrir_exclusao_massiva
            elif id_op == "copiador_produtos":
                cmd_original = self.abrir_copiador_produtos
            elif id_op == "compactador_packs":
                cmd_original = self.abrir_compactador_packs
            elif id_op == "organizador_conferencia":
                cmd_original = self.abrir_organizador_conferencia
            elif id_op == "renomeador_packs":
                cmd_original = self.abrir_renomeador_packs
            elif id_op == "criador_packs":
                cmd_original = self.abrir_criador_packs
            elif id_op == "rastreador":
                cmd_original = self.abrir_rastreador
            elif id_op == "conferencia":
                cmd_original = self.abrir_conferencia
            elif id_op == "limpador":
                cmd_original = self.abrir_limpador
            elif id_op == "movimentar":
                cmd_original = self.abrir_movimentar
            elif id_op == "renomeador":
                cmd_original = self.abrir_renomeador
            elif id_op == "transferidor":
                cmd_original = self.abrir_transferidor
            elif id_op == "extrair":
                cmd_original = self.abrir_extrair
            else:
                cmd_original = lambda n=nome: self.tela_em_breve(n)
            
            # Cria um comando envelopado para registrar o uso antes de abrir a tela
            def criar_comando(op_id, cmd_base):
                return lambda: [self.registrar_abertura(op_id), cmd_base()]

            btn = ctk.CTkButton(item_frame, text="ABRIR", width=110, height=34, corner_radius=8,
                                fg_color=btn_fg, hover_color=btn_hover, text_color=btn_text_color,
                                font=("Segoe UI", 12, "bold"),
                                command=criar_comando(id_op, cmd_original))
            btn.pack(side="right", padx=25, pady=25)

    # --- FUNÇÕES DE ABERTURA DE MÓDULOS ---

    def abrir_exclusao_massiva(self):
        self.clear_container()
        self.render_top_bar()
        frame = ExclusaoMassivaFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_copiador_produtos(self):
        self.clear_container()
        self.render_top_bar()
        frame = CopiadorProdutosFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_compactador_packs(self):
        self.clear_container()
        self.render_top_bar()
        frame = CompactadorPacksFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_organizador_conferencia(self):
        self.clear_container()
        self.render_top_bar()
        frame = OrganizadorConferenciaFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_renomeador_packs(self):
        self.clear_container()
        self.render_top_bar()
        frame = RenomeadorPacksFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_criador_packs(self):
        self.clear_container()
        self.render_top_bar()
        frame = CriadorPacksFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_rastreador(self):
        self.clear_container()
        self.render_top_bar()
        frame = RastreadorLinksFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_conferencia(self):
        self.clear_container()
        self.render_top_bar()
        frame = ConferenciaVideosFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_limpador(self):
        self.clear_container()
        self.render_top_bar()
        frame = LimpadorUrlsFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_movimentar(self):
        self.clear_container()
        self.render_top_bar()
        frame = MovimentarVideosFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_renomeador(self):
        self.clear_container()
        self.render_top_bar()
        frame = RenomeadorFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_transferidor(self):
        self.clear_container()
        self.render_top_bar()
        frame = FileTransferFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def abrir_extrair(self):
        self.clear_container()
        self.render_top_bar()
        frame = ExtrairArquivosFrame(self.main_container)
        frame.pack(fill="both", expand=True, padx=20, pady=10)

    def tela_em_breve(self, nome):
        self.clear_container()
        self.render_top_bar()
        msg_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        msg_frame.pack(expand=True)
        
        ctk.CTkLabel(msg_frame, text=f"A ferramenta '{nome}'\nestá em fase de desenvolvimento.", 
                     font=("Segoe UI", 18, "bold")).pack(pady=10)
        
        ctk.CTkButton(msg_frame, text="Voltar ao Dashboard", command=self.show_main_menu).pack(pady=20)

if __name__ == "__main__":
    app = AppFacilitadores()
    app.mainloop()