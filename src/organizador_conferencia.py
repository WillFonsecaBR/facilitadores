"""
FERRAMENTA: ORGANIZADOR DE CONFERÊNCIA - VÍDEOS & IMAGENS (FACILITADORES) - VERSÃO ULTRA PERFORMANCE 3.0
LÓGICA:
1. VARREDURA EXCLUSIVA DA RAIZ: Usa os.scandir() para listar apenas os arquivos diretamente na raiz,
   ignorando completamente qualquer arquivo que já esteja dentro de subpastas.
2. MODOS DE OPERAÇÃO:
   - MODO VÍDEOS: Agrupa vídeos da raiz em pastas sequenciais "SEPARACAO_[NÚMERO]".
   - MODO IMAGENS: Agrupa imagens da raiz em pastas aleatórias "[NOME_DA_PASTA_RAIZ]_[NÚMERO_RANDÔMICO_5_DÍGITOS]".
3. ESTRUTURA INTERNA:
   - Ambos os modos criam duas subpastas vazias dentro de cada lote: "00_COM_MD" e "00_FINALIZADO".
4. MOVIMENTAÇÃO ATÔMICA: Usa os.rename() para mover os arquivos instantaneamente.
5. INTERFACE THREAD-SAFE: Atualização de progresso e logs via polling a cada 100ms para evitar travamentos.
"""

import os
import random
import shutil
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk


class OrganizadorConferenciaFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.allowed_video_ext = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]
        self.allowed_image_ext = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".heic"]
        
        self.is_running = False
        self.pausado = False
        self.stop_requested = False
        self.start_time = 0
        self.root_dir = None
        self.modo_execucao = "videos"  # "videos" ou "imagens"
        
        # Variáveis de controle de UI (Thread-Safe)
        self.ui_progresso = 0.0
        self.ui_stats_text = "Pastas Criadas: 0 | Arquivos Organizados: 0/0"
        self.ui_status_text = "Status: Aguardando Comando"
        self.log_queue = []
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Título
        ctk.CTkLabel(self, text="ORGANIZADOR DE CONFERÊNCIA", 
                     font=("Segoe UI", 20, "bold")).pack(pady=(10, 15))

        # Painel de Configurações
        config_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        config_frame.pack(fill="x", padx=20, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        # 1. Seleção de Pasta Raiz
        ctk.CTkLabel(config_frame, text="Pasta Raiz:", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=15, pady=12, sticky="w")
        
        folder_subframe = ctk.CTkFrame(config_frame, fg_color="transparent")
        folder_subframe.grid(row=0, column=1, padx=15, pady=12, sticky="ew")
        
        self.btn_folder = ctk.CTkButton(folder_subframe, text="📁 SELECIONAR PASTA", 
                                        command=self.select_folder, fg_color="#3d3d3d", width=150)
        self.btn_folder.pack(side="left")
        
        self.lbl_folder = ctk.CTkLabel(folder_subframe, text="Nenhum diretório selecionado", text_color="gray")
        self.lbl_folder.pack(side="left", padx=10)

        # 2. Quantidade de Arquivos por Pasta
        ctk.CTkLabel(config_frame, text="Quantidade por Pasta:", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, padx=15, pady=12, sticky="w")
        self.entry_qty = ctk.CTkEntry(config_frame, placeholder_text="Ex: 50 (Obrigatório)", 
                                             height=35, fg_color="#0f0f0f")
        self.entry_qty.grid(row=1, column=1, padx=15, pady=12, sticky="ew")

        # Terminal de Logs
        self.terminal = ctk.CTkTextbox(self, height=250, font=("Courier New", 12), 
                                       fg_color="#000000", text_color="#2ecc71")
        self.terminal.pack(fill="both", expand=True, padx=20, pady=10)

        # Barra de Status e Progresso
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20)
        
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=800, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=5)

        self.lbl_stats = ctk.CTkLabel(self.status_frame, text="Pastas Criadas: 0 | Arquivos Organizados: 0/0", 
                                      font=("Segoe UI", 11, "bold"))
        self.lbl_stats.pack(pady=2)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Aguardando Comando", font=("Segoe UI", 12))
        self.lbl_status.pack(pady=(0, 10))

        # Controles
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)

        # Botão 1: Organizar Vídeos (Verde)
        self.btn_start_videos = ctk.CTkButton(self.ctrl_frame, text="▶ ORGANIZAR VÍDEOS", fg_color="#2ecc71", 
                                       hover_color="#27ae60", width=190, height=45, 
                                       font=("Segoe UI", 12, "bold"), command=lambda: self.iniciar("videos"))
        self.btn_start_videos.grid(row=0, column=0, padx=4)

        # Botão 2: Organizar Imagens (Azul)
        self.btn_start_images = ctk.CTkButton(self.ctrl_frame, text="🖼️ ORGANIZAR IMAGENS", fg_color="#3498db", 
                                       hover_color="#2980b9", width=190, height=45, 
                                       font=("Segoe UI", 12, "bold"), command=lambda: self.iniciar("imagens"))
        self.btn_start_images.grid(row=0, column=1, padx=4)

        # Botão 3: Pausar
        self.btn_pause = ctk.CTkButton(self.ctrl_frame, text="PAUSAR", state="disabled", 
                                       width=110, height=45, command=self.alternar_pausa)
        self.btn_pause.grid(row=0, column=2, padx=4)

        # Botão 4: Parar
        self.btn_stop = ctk.CTkButton(self.ctrl_frame, text="PARAR", fg_color="#e74c3c", 
                                      width=110, height=45, state="disabled", command=self.stop)
        self.btn_stop.grid(row=0, column=3, padx=4)

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
                
                # Limita tamanho do terminal para evitar lentidão
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
        if self.pausado:
            self.log("Processo pausado pelo usuário.")
        else:
            self.log("Processo retomado.")

    def stop(self):
        self.stop_requested = True
        self.log("Solicitando parada segura...")

    def iniciar(self, modo):
        if not self.root_dir or not self.root_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta raiz válida.")
            return

        # Validação obrigatória da quantidade por pasta
        try:
            self.qty_per_folder = int(self.entry_qty.get().strip())
            if self.qty_per_folder <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Aviso", "A quantidade de arquivos deve ser um número inteiro maior que zero.")
            return

        self.modo_execucao = modo
        self.is_running = True
        self.pausado = False
        self.stop_requested = False
        
        # Bloqueia controles de navegação e inputs
        self.btn_start_videos.configure(state="disabled")
        self.btn_start_images.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
        self.entry_qty.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="PAUSAR")
        self.btn_stop.configure(state="normal")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="disabled")

        self.terminal.delete("1.0", "end")
        self.log_queue = []
        self.atualizar_interface_periodico()

        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            self.log(f"Iniciando varredura rápida no modo: {self.modo_execucao.upper()}...")
            self.start_time = time.time()
            
            arquivos_disponiveis = []
            root_path_str = str(self.root_dir)
            
            # Filtros de extensão por modo
            extensoes_alvo = self.allowed_video_ext if self.modo_execucao == "videos" else self.allowed_image_ext
            tipo_nome = "vídeos" if self.modo_execucao == "videos" else "imagens"

            # OTIMIZAÇÃO: os.scandir() lê apenas arquivos da raiz, ignorando subpastas nativamente
            with os.scandir(root_path_str) as entries:
                for entry in entries:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            name = entry.name
                            if not name.startswith(".") and not name.startswith("._"):
                                ext = os.path.splitext(name)[1].lower()
                                if ext in extensoes_alvo:
                                    arquivos_disponiveis.append(Path(entry.path))
                    except Exception:
                        continue

            total_arquivos = len(arquivos_disponiveis)
            self.log(f"Varredura concluída! Encontrados {total_arquivos} {tipo_nome} qualificados na raiz.")

            if total_arquivos == 0:
                self.log(f"Nenhum arquivo qualificado encontrado diretamente na raiz para o modo {self.modo_execucao.upper()}.")
                return

            # Calcula a quantidade de pastas necessárias
            sobra = total_arquivos % self.qty_per_folder
            pastas_a_criar = total_arquivos // self.qty_per_folder
            if sobra > 0:
                pastas_a_criar += 1

            self.log(f"Planejado criar: {pastas_a_criar} pasta(s) de separação.")

            pastas_criadas = 0
            arquivos_organizados = 0
            erros = 0

            nome_pasta_raiz = self.root_dir.name

            for p in range(1, pastas_a_criar + 1):
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)
                if self.stop_requested: break

                # Seleciona fatias de arquivos para cada pasta
                lote_arquivos = arquivos_disponiveis[(p-1)*self.qty_per_folder : p*self.qty_per_folder]
                qtd_lote = len(lote_arquivos)

                # Define o nome da pasta de acordo com o modo de execução
                if self.modo_execucao == "videos":
                    # Lógica de Vídeo: SEPARACAO_1, SEPARACAO_2, etc.
                    separacao_dir = self.root_dir / f"SEPARACAO_{p}"
                    while separacao_dir.exists():
                        separacao_dir = self.root_dir / f"SEPARACAO_{p}_{random.randint(100, 999)}"
                else:
                    # Lógica de Imagem: [NOME_PASTA_RAIZ]_[NUMERO_RANDOMICO_5_DIGITOS]
                    num_random = f"{random.randint(10000, 99999)}"
                    separacao_dir = self.root_dir / f"{nome_pasta_raiz}_{num_random}"
                    while separacao_dir.exists():
                        num_random = f"{random.randint(10000, 99999)}"
                        separacao_dir = self.root_dir / f"{nome_pasta_raiz}_{num_random}"

                separacao_dir.mkdir(parents=True, exist_ok=True)
                self.log(f"\nCriando pasta: {separacao_dir.name}")

                # Cria as subpastas vazias internas requeridas
                (separacao_dir / "00_COM_MD").mkdir(parents=True, exist_ok=True)
                (separacao_dir / "00_FINALIZADO").mkdir(parents=True, exist_ok=True)

                for arq_path in lote_arquivos:
                    while self.pausado and not self.stop_requested:
                        time.sleep(0.1)
                    if self.stop_requested: break

                    dest_arq = separacao_dir / arq_path.name
                    
                    # Move o arquivo de forma instantânea (os.rename)
                    try:
                        os.rename(str(arq_path), str(dest_arq))
                        arquivos_organizados += 1
                        self.log(f"MOVIDO: {arq_path.name} -> {separacao_dir.name}/")
                    except Exception as e:
                        erros += 1
                        self.log(f"ERRO ao mover {arq_path.name}: {e}")

                    # Atualiza progresso e estatísticas
                    self.ui_progresso = arquivos_organizados / total_arquivos
                    self.ui_stats_text = f"Pastas Criadas: {pastas_criadas+1}/{pastas_a_criar} | Organizados: {arquivos_organizados}/{total_arquivos}"
                    self.ui_status_text = f"Organizando: {arquivos_organizados}/{total_arquivos}"

                pastas_criadas += 1

            # Resumo Final no Terminal
            duracao = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
            self.log("\n" + "="*40)
            self.log("RELATÓRIO FINAL DA OPERAÇÃO")
            self.log(f"Modo Executado: {self.modo_execucao.upper()}")
            self.log(f"Duração Total: {duracao}")
            self.log(f"Pastas Criadas: {pastas_criadas}")
            self.log(f"Arquivos Organizados: {arquivos_organizados}")
            self.log(f"Erros/Falhas: {erros}")
            self.log("="*40)

        except Exception as e:
            self.log(f"ERRO CRÍTICO NO PROCESSO: {e}")
        finally:
            self.finalizar()

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
        self.btn_start_videos.configure(state="normal")
        self.btn_start_images.configure(state="normal")
        self.btn_folder.configure(state="normal")
        self.entry_qty.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="normal")
            
        messagebox.showinfo("Fim", "Processo de organização finalizado.")