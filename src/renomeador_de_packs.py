"""
FERRAMENTA: RENOMEADOR DE PACKS (FACILITADORES) - VERSÃO ULTRA PERFORMANCE 4.3
LÓGICA:
1. VARREDURA: Identifica todas as subpastas de primeiro nível na pasta raiz (ignora arquivos e a pasta '00 - IMAGENS').
2. CONTAGEM: Conta de forma ultra-rápida todos os vídeos qualificados dentro de cada pasta principal.
3. RENOMEAÇÃO DA PASTA PAI: Aplica o padrão de nome substituindo {NUMERO} por 5 dígitos aleatórios e {QTD_VIDEOS} pela contagem.
4. EXCLUSÃO DE LOGS/READMES: Exclui arquivos log.txt e readme.txt (case-insensitive) de dentro da pasta renomeada.
5. RENOMEAÇÃO DA SUBPASTA: Identifica a subpasta interna (segundo nível) e a renomeia com o mesmo nome da pasta pai.
6. MOVIMENTAÇÃO: Move a subpasta renomeada para a pasta central "00 - IMAGENS" na raiz do projeto.
7. RELATÓRIO: Salva todos os novos nomes gerados no arquivo "PACKS_NAME.TXT" na raiz.
"""

import os
import random
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk


class RenomeadorPacksFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.allowed_video_ext = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]
        self.is_running = False
        self.pausado = False
        self.stop_requested = False
        self.root_dir = None
        
        # Variáveis de controle de UI (Thread-Safe)
        self.ui_progresso = 0.0
        self.ui_stats_text = "Pastas Processadas: 0/0 | Erros: 0"
        self.ui_status_text = "Status: Aguardando Comando"
        self.log_queue = []
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Título
        ctk.CTkLabel(self, text="RENOMEADOR E ORGANIZADOR DE PACKS", 
                     font=("Segoe UI", 20, "bold")).pack(pady=(10, 15))

        # Painel de Configurações
        config_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        config_frame.pack(fill="x", padx=20, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        # 1. Seleção de Pasta Raiz
        ctk.CTkLabel(config_frame, text="Diretório Raiz:", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=15, pady=12, sticky="w")
        
        folder_subframe = ctk.CTkFrame(config_frame, fg_color="transparent")
        folder_subframe.grid(row=0, column=1, padx=15, pady=12, sticky="ew")
        
        self.btn_folder = ctk.CTkButton(folder_subframe, text="📁 SELECIONAR PASTA", 
                                        command=self.select_folder, fg_color="#3d3d3d", width=150)
        self.btn_folder.pack(side="left")
        
        self.lbl_folder = ctk.CTkLabel(folder_subframe, text="Nenhum diretório selecionado", text_color="gray")
        self.lbl_folder.pack(side="left", padx=10)

        # 2. Padrão de Nome
        ctk.CTkLabel(config_frame, text="Padrão de Nome:", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, padx=15, pady=12, sticky="w")
        self.entry_pattern = ctk.CTkEntry(config_frame, placeholder_text="Ex: Curiosity Facts Video Pack #{NUMERO} - {QTD_VIDEOS} Clips", 
                                             height=35, fg_color="#0f0f0f")
        self.entry_pattern.grid(row=1, column=1, padx=15, pady=12, sticky="ew")
        self.entry_pattern.insert(0, "Curiosity Facts Video Pack #{NUMERO} - {QTD_VIDEOS} Clips")

        # Terminal de Logs
        self.terminal = ctk.CTkTextbox(self, height=250, font=("Courier New", 12), 
                                       fg_color="#000000", text_color="#3498db")
        self.terminal.pack(fill="both", expand=True, padx=20, pady=10)

        # Barra de Status e Progresso
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20)
        
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=800, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=5)

        self.lbl_stats = ctk.CTkLabel(self.status_frame, text="Pastas Processadas: 0/0 | Erros: 0", 
                                      font=("Segoe UI", 11, "bold"))
        self.lbl_stats.pack(pady=2)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Aguardando Comando", font=("Segoe UI", 12))
        self.lbl_status.pack(pady=(0, 10))

        # Controles
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.ctrl_frame, text="▶ INICIAR PROCESSO", fg_color="#2ecc71", 
                                       hover_color="#27ae60", width=220, height=45, 
                                       font=("Segoe UI", 13, "bold"), command=self.iniciar)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_pause = ctk.CTkButton(self.ctrl_frame, text="PAUSAR", state="disabled", 
                                       width=120, height=45, command=self.alternar_pausa)
        self.btn_pause.grid(row=0, column=1, padx=5)

        self.btn_stop = ctk.CTkButton(self.ctrl_frame, text="PARAR", fg_color="#e74c3c", 
                                      width=120, height=45, state="disabled", command=self.stop)
        self.btn_stop.grid(row=0, column=2, padx=5)

    def log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        self.log_queue.append(f"[{timestamp}] {msg}")

    def atualizar_interface_periodico(self):
        """Atualiza a interface gráfica de forma segura a partir da Main Thread."""
        if self.is_running:
            if self.log_queue:
                lote = self.log_queue[:]
                self.log_queue = self.log_queue[len(lote):]
                self.terminal.insert("end", "\n".join(lote) + "\n")
                
                linhas_total = float(self.terminal.index('end-1c').split('.')[0])
                if linhas_total > 1000:
                    self.terminal.delete("1.0", f"{int(linhas_total - 1000)}.0")
                self.terminal.see("end")
            
            self.progress_bar.set(self.ui_progresso)
            self.lbl_stats.configure(text=self.ui_stats_text)
            self.lbl_status.configure(text=self.ui_status_text)
            
            self.after(100, self.atualizar_interface_periodico)

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.root_dir = Path(path)
            self.lbl_folder.configure(text=str(self.root_dir), text_color="white")

    def alternar_pausa(self):
        self.pausado = not self.pausado
        self.btn_pause.configure(text="RETOMAR" if self.pausado else "PAUSAR")

    def stop(self):
        self.stop_requested = True
        self.log("Solicitando parada segura...")

    def iniciar(self):
        if not self.root_dir or not self.root_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta raiz válida.")
            return

        self.pattern = self.entry_pattern.get().strip()
        if not self.pattern:
            messagebox.showwarning("Aviso", "O padrão de nome não pode estar vazio.")
            return

        self.is_running = True
        self.pausado = False
        self.stop_requested = False
        
        # Bloqueia controles de navegação e inputs
        self.btn_start.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
        self.entry_pattern.configure(state="disabled")
        self.btn_pause.configure(state="normal")
        self.btn_stop.configure(state="normal")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="disabled")

        self.terminal.delete("1.0", "end")
        self.log_queue = []
        self.atualizar_interface_periodico()

        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            self.log("Identificando pastas principais na raiz...")
            
            # Coleta apenas diretórios de primeiro nível (ignora arquivos e a pasta de destino 00 - IMAGENS)
            pastas_principais = []
            with os.scandir(str(self.root_dir)) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in ("00 - IMAGENS", "00_IMAGENS", "00_CONFERENCIA"):
                            pastas_principais.append(Path(entry.path))

            total_pastas = len(pastas_principais)
            self.log(f"Encontradas {total_pastas} pastas qualificadas para processamento.")

            if total_pastas == 0:
                self.log("Nenhuma pasta encontrada para renomear.")
                return

            # Cria a pasta central de imagens
            imagens_root = self.root_dir / "00 - IMAGENS"
            imagens_root.mkdir(exist_ok=True)

            nomes_gerados = []
            processadas = 0
            erros = 0

            for idx, pasta_pai in enumerate(pastas_principais, 1):
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)
                if self.stop_requested: break

                self.log(f"\nProcessando pasta: {pasta_pai.name}")
                self.ui_status_text = f"Analisando: {pasta_pai.name}"

                try:
                    # 1. Conta a quantidade de vídeos qualificados dentro da pasta pai de forma recursiva
                    qtd_videos = self.contar_videos(pasta_pai)
                    self.log(f"Vídeos encontrados: {qtd_videos}")

                    # 2. Gera o número randômico de 5 dígitos
                    random_num = f"{random.randint(10000, 99999)}"

                    # 3. Formata o novo nome da pasta pai
                    novo_nome_pai = self.pattern.replace("{NUMERO}", random_num).replace("{QTD_VIDEOS}", str(qtd_videos))
                    
                    # OTIMIZAÇÃO CRÍTICA: chr(92) representa a barra invertida (\) de forma segura sem quebrar a sintaxe do VS Code
                    for char in [chr(92), '/', ':', '*', '?', '"', '<', '>', '|']:
                        novo_nome_pai = novo_nome_pai.replace(char, "_")

                    novo_caminho_pai = self.root_dir / novo_nome_pai

                    # Evita colisão de nomes
                    if novo_caminho_pai.exists():
                        novo_nome_pai = f"{novo_nome_pai}_{random.randint(100, 999)}"
                        novo_caminho_pai = self.root_dir / novo_nome_pai

                    # 4. Renomeia a pasta pai
                    os.rename(str(pasta_pai), str(novo_caminho_pai))
                    self.log(f"Renomeado Pai: {pasta_pai.name} -> {novo_nome_pai}")

                    # 5. Exclui arquivos de log e readme de dentro da pasta renomeada
                    self.excluir_log_readme(novo_caminho_pai)

                    # 6. Encontra a subpasta interna (segunda subpasta)
                    subpasta_interna = self.obter_subpasta(novo_caminho_pai)
                    if subpasta_interna:
                        # Renomeia a subpasta interna com o exato mesmo nome da pasta pai
                        novo_caminho_sub = novo_caminho_pai / novo_nome_pai
                        os.rename(str(subpasta_interna), str(novo_caminho_sub))
                        self.log(f"Renomeado Filho: {subpasta_interna.name} -> {novo_nome_pai}")

                        # 7. Move a subpasta interna para a pasta central "00 - IMAGENS"
                        destino_final = imagens_root / novo_nome_pai
                        # Se já existir uma pasta de mesmo nome no destino, renomeia para evitar substituição
                        if destino_final.exists():
                            destino_final = imagens_root / f"{novo_nome_pai}_{random.randint(10, 99)}"
                        os.rename(str(novo_caminho_sub), str(destino_final))
                        self.log(f"Movido Filho para: 00 - IMAGENS/{destino_final.name}")
                    else:
                        self.log("Aviso: Nenhuma subpasta interna encontrada para mover.")

                    nomes_gerados.append(novo_nome_pai)
                    processadas += 1

                except Exception as e:
                    erros += 1
                    self.log(f"ERRO ao processar {pasta_pai.name}: {e}")

                # Atualiza progresso e estatísticas
                self.ui_progresso = idx / total_pastas
                self.ui_stats_text = f"Pastas Processadas: {processadas}/{total_pastas} | Erros: {erros}"

            # 8. Salva a lista de nomes gerados no arquivo PACKS_NAME.TXT
            if nomes_gerados:
                self.salvar_lista_nomes(nomes_gerados)

            # Resumo Final no Terminal
            self.log("\n" + "="*40)
            self.log("RESUMO FINAL DA OPERAÇÃO")
            self.log(f"Pastas Processadas com Sucesso: {processadas}")
            self.log(f"Erros Encontrados: {erros}")
            self.log(f"Lista salva em: {self.root_dir.name}/PACKS_NAME.TXT")
            self.log("="*40)

        except Exception as e:
            self.log(f"ERRO CRÍTICO NO PROCESSO: {e}")
        finally:
            self.finalizar()

    def contar_videos(self, pasta_caminho):
        """Conta vídeos de forma ultra-rápida usando os.scandir recursivo."""
        count = 0
        try:
            for entry in os.scandir(str(pasta_caminho)):
                if entry.is_file(follow_symlinks=False):
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in self.allowed_video_ext:
                        count += 1
                elif entry.is_dir(follow_symlinks=False):
                    count += self.contar_videos(Path(entry.path))
        except:
            pass
        return count

    def obter_subpasta(self, pasta_pai):
        """Retorna a primeira subpasta encontrada dentro do diretório."""
        try:
            for entry in os.scandir(str(pasta_pai)):
                if entry.is_dir(follow_symlinks=False):
                    return Path(entry.path)
        except:
            pass
        return None

    def excluir_log_readme(self, pasta_caminho):
        """Varre a pasta renomeada e exclui arquivos de log e readme (case-insensitive)."""
        try:
            for root, dirs, files in os.walk(str(pasta_caminho)):
                for file in files:
                    file_lower = file.lower()
                    if file_lower in ("log.txt", "readme.txt", "log", "readme"):
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            self.log(f"Excluído arquivo indesejado: {file} de {Path(root).name}")
                        except Exception as e:
                            self.log(f"Erro ao excluir {file}: {e}")
        except Exception as e:
            self.log(f"Erro na varredura de exclusão de logs/readmes: {e}")

    def salvar_lista_nomes(self, lista_nomes):
        """Escreve a lista de nomes gerados no arquivo PACKS_NAME.TXT."""
        caminho_txt = self.root_dir / "PACKS_NAME.TXT"
        try:
            with open(caminho_txt, "w", encoding="utf-8") as f:
                for nome in lista_nomes:
                    f.write(f"{nome}\n")
            self.log("Arquivo PACKS_NAME.TXT gerado com sucesso.")
        except Exception as e:
            self.log(f"Erro ao salvar arquivo PACKS_NAME.TXT: {e}")

    def finalizar(self):
        self.after(0, self.finalizar_main_thread)

    def finalizar_main_thread(self):
        self.is_running = False
        
        # Despeja logs finais restantes
        if self.log_queue:
            self.terminal.insert("end", "\n".join(self.log_queue) + "\n")
            self.log_queue = []
            self.terminal.see("end")
            
        self.progress_bar.set(self.ui_progresso)
        self.lbl_stats.configure(text=self.ui_stats_text)
        self.lbl_status.configure(text="Concluído." if not self.stop_requested else "Interrompido.")
        
        # Libera controles de navegação e inputs
        self.btn_start.configure(state="normal")
        self.btn_folder.configure(state="normal")
        self.entry_pattern.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="normal")
            
        messagebox.showinfo("Fim", "Processo de renomeação de packs finalizado.")