"""
FERRAMENTA: MOVIMENTAR MÍDIAS (FACILITADORES) - VERSÃO ULTRA VELOCIDADE 4.2
LÓGICA:
1. VÍDEOS: Move subpastas -> RAIZ de forma instantânea via os.rename() (Apenas no Modo Completo).
2. IMAGENS: Move subpastas -> RAIZ/00_IMAGENS de forma instantânea via os.rename() (Em ambos os modos).
3. MODOS DE OPERAÇÃO:
   - "completo": Move vídeos para a raiz e imagens para 00_IMAGENS.
   - "imagens_apenas": Move apenas as imagens para 00_IMAGENS, mantendo os vídeos intocados em suas pastas.
4. CONTROLE DE FLUXO: Botões dedicados para Iniciar, Pausar/Retomar e Parar de forma segura.
5. MONITORAMENTO PRO (THREAD-SAFE): Logs e progresso são atualizados em lote a cada 100ms,
   evitando o travamento do Tkinter e reduzindo o tempo de processamento de horas para minutos.
6. RELATÓRIO: Duração total incluída no resumo final.
"""

import os
import shutil
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk


class MovimentarVideosFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.allowed_video_ext = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]
        self.allowed_image_ext = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".heic"]
        
        self.is_running = False
        self.pausado = False
        self.stop_requested = False
        self.start_time = 0
        self.modo_execucao = "completo"  # "completo" ou "imagens_apenas"
        
        # Variáveis de controle de UI (Thread-Safe)
        self.ui_progresso = 0.0
        self.ui_files_text = "Arquivos: 0/0"
        self.ui_timer_text = "Tempo: 00:00 | Restante: ~00:00"
        self.ui_errors_text = "Erros: 0"
        self.log_queue = []
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Título
        ctk.CTkLabel(self, text="MOVIMENTAR VÍDEOS & IMAGENS", 
                     font=("Segoe UI", 20, "bold")).pack(pady=(10, 20))

        # Seleção de Pasta
        frame_path = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        frame_path.pack(fill="x", padx=20, pady=10)

        self.btn_folder = ctk.CTkButton(frame_path, text="📁 SELECIONAR PASTA RAIZ", 
                                        command=self.select_folder, fg_color="#3d3d3d")
        self.btn_folder.grid(row=0, column=0, padx=15, pady=15)
        
        self.lbl_folder = ctk.CTkLabel(frame_path, text="Nenhum diretório selecionado", text_color="gray")
        self.lbl_folder.grid(row=0, column=1, sticky="w")

        # Terminal de Logs
        self.terminal = ctk.CTkTextbox(self, height=300, font=("Courier New", 12), 
                                       fg_color="#000000", text_color="#2ecc71")
        self.terminal.pack(fill="both", padx=20, pady=10)

        # Painel de Status Detalhado
        self.status_container = ctk.CTkFrame(self, fg_color="transparent")
        self.status_container.pack(fill="x", padx=20)
        self.status_container.grid_columnconfigure((0,1,2), weight=1)

        self.lbl_files = ctk.CTkLabel(self.status_container, text="Arquivos: 0/0", font=("Segoe UI", 11, "bold"))
        self.lbl_files.grid(row=0, column=0, sticky="w")

        self.lbl_timer = ctk.CTkLabel(self.status_container, text="Tempo: 00:00 | Restante: ~00:00", font=("Segoe UI", 11))
        self.lbl_timer.grid(row=0, column=1)

        self.lbl_errors = ctk.CTkLabel(self.status_container, text="Erros: 0", text_color="#e74c3c", font=("Segoe UI", 11, "bold"))
        self.lbl_errors.grid(row=0, column=2, sticky="e")

        # Barra de Progresso
        self.progress_bar = ctk.CTkProgressBar(self, width=800, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(5, 20), padx=20)

        # Controles
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)

        # Botão 1: Mover Tudo (Completo)
        self.btn_start = ctk.CTkButton(self.ctrl_frame, text="▶ MOVER VÍDEOS & IMAGENS", fg_color="#2ecc71", 
                                       hover_color="#27ae60", width=210, height=45, 
                                       font=("Segoe UI", 11, "bold"), command=lambda: self.iniciar("completo"))
        self.btn_start.grid(row=0, column=0, padx=4)

        # Botão 2: Mover Apenas Imagens
        self.btn_start_images = ctk.CTkButton(self.ctrl_frame, text="🖼️ SEPARAR APENAS IMAGENS", fg_color="#9b59b6", 
                                       hover_color="#8e44ad", width=210, height=45, 
                                       font=("Segoe UI", 11, "bold"), command=lambda: self.iniciar("imagens_apenas"))
        self.btn_start_images.grid(row=0, column=1, padx=4)

        # Botão 3: Pausar / Retomar (Adicionado)
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
        """Despeja logs e atualiza a barra de progresso a cada 100ms na Thread Principal."""
        if self.is_running:
            if self.log_queue:
                lote = self.log_queue[:]
                self.log_queue = self.log_queue[len(lote):]
                self.terminal.insert("end", "\n".join(lote) + "\n")
                
                # Evita estouro de memória no terminal
                linhas_total = float(self.terminal.index('end-1c').split('.')[0])
                if linhas_total > 1000:
                    self.terminal.delete("1.0", f"{int(linhas_total - 1000)}.0")
                self.terminal.see("end")
            
            # Atualiza elementos visuais de forma suave
            self.progress_bar.set(self.ui_progresso)
            self.lbl_files.configure(text=self.ui_files_text)
            self.lbl_errors.configure(text=self.ui_errors_text)
            self.lbl_timer.configure(text=self.ui_timer_text)
            
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
        if not hasattr(self, 'root_dir') or not self.root_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta válida.")
            return

        self.modo_execucao = modo
        self.is_running = True
        self.pausado = False
        self.stop_requested = False
        
        self.btn_start.configure(state="disabled")
        self.btn_start_images.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="PAUSAR")
        self.btn_stop.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.start_time = time.time()
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="disabled")

        self.log_queue = []
        self.atualizar_interface_periodico()

        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        try:
            self.log(f"Iniciando varredura rápida no modo: {self.modo_execucao.upper()}...")
            img_dir = self.root_dir / "00_IMAGENS"
            img_dir.mkdir(exist_ok=True)
            
            img_dir_str = str(img_dir)
            root_dir_str = str(self.root_dir)

            todos_arquivos = []
            
            # OTIMIZAÇÃO: os.walk modificado in-place para não entrar nas pastas já processadas
            for root, dirs, files in os.walk(root_dir_str):
                if self.stop_requested: 
                    break
                
                # Poda as pastas de imagens e conferência para o os.walk ignorá-las completamente
                dirs[:] = [d for d in dirs if d not in ("00_IMAGENS", "00_CONFERENCIA")]
                
                for file in files:
                    if not file.startswith(".") and not file.startswith("._"):
                        ext = os.path.splitext(file)[1].lower()
                        
                        # Se o modo for "imagens_apenas", ignora a varredura de vídeos para poupar processamento
                        if self.modo_execucao == "imagens_apenas":
                            if ext in self.allowed_image_ext:
                                todos_arquivos.append((os.path.join(root, file), file, ext))
                        else:
                            if ext in self.allowed_video_ext or ext in self.allowed_image_ext:
                                todos_arquivos.append((os.path.join(root, file), file, ext))

            total = len(todos_arquivos)
            if total == 0:
                self.log("Nenhum arquivo qualificado encontrado para este modo.")
                return

            self.log(f"Varredura concluída! {total} arquivos prontos para movimentação.")

            movidos_v = 0
            movidos_i = 0
            erros = 0

            for i, (arq_path, name, ext) in enumerate(todos_arquivos, 1):
                # Lógica de Pausa
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)
                
                if self.stop_requested: 
                    break
                
                try:
                    if ext in self.allowed_video_ext:
                        dest_path = os.path.join(root_dir_str, name)
                        tipo = "VÍDEO"
                    else:
                        dest_path = os.path.join(img_dir_str, name)
                        tipo = "IMAGEM"

                    if arq_path != dest_path:
                        if os.path.exists(dest_path):
                            nome_sem_ext, _ = os.path.splitext(name)
                            novo_nome = f"{nome_sem_ext}_{int(time.time())}{ext}"
                            dest_path = os.path.join(os.path.dirname(dest_path), novo_nome)
                        
                        # OTIMIZAÇÃO CRÍTICA: os.rename() altera apenas os metadados (instantâneo)
                        try:
                            os.rename(arq_path, dest_path)
                        except OSError:
                            # Fallback seguro caso ocorra algum erro de permissão ou partição
                            shutil.move(arq_path, dest_path)
                            
                        if tipo == "VÍDEO": 
                            movidos_v += 1
                        else: 
                            movidos_i += 1
                            
                        self.log(f"MOVIDO: {name}")

                except Exception as e:
                    erros += 1
                    self.log(f"ERRO: {name} | {e}")

                # Atualiza variáveis leves em memória (Thread-Safe)
                self.ui_progresso = i / total
                elapsed = time.time() - self.start_time
                avg = elapsed / i if i > 0 else 0
                eta = avg * (total - i)
                
                self.ui_files_text = f"Arquivos: {i}/{total}"
                self.ui_errors_text = f"Erros: {erros}"
                self.ui_timer_text = f"Tempo: {time.strftime('%M:%S', time.gmtime(elapsed))} | Restante: ~{time.strftime('%M:%S', time.gmtime(eta))}"

            # Só limpa pastas vazias se não tiver sido interrompido
            if not self.stop_requested:
                self.log("Limpando pastas vazias...")
                self.remover_pastas_vazias(root_dir_str)

            duracao_total = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
            
            self.log("\n" + "="*40)
            self.log("RELATÓRIO FINAL")
            self.log(f"Modo Executado: {self.modo_execucao.upper()}")
            self.log(f"Duração Total: {duracao_total}")
            self.log(f"Vídeos na Raiz: {movidos_v}")
            self.log(f"Imagens em 00_IMAGENS: {movidos_i}")
            self.log(f"Erros: {erros}")
            self.log("="*40)

        except Exception as e:
            self.log(f"ERRO CRÍTICO NO PROCESSO: {e}")
        finally:
            self.finalizar()

    def remover_pastas_vazias(self, path):
        for root, dirs, files in os.walk(path, topdown=False):
            for name in dirs:
                dir_path = os.path.join(root, name)
                if "00_IMAGENS" in dir_path or "00_CONFERENCIA" in dir_path: continue
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except: pass

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
        self.lbl_files.configure(text=self.ui_files_text)
        self.lbl_errors.configure(text=self.ui_errors_text)
        self.lbl_timer.configure(text=self.ui_timer_text)
        
        self.btn_start.configure(state="normal")
        self.btn_start_images.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="PAUSAR")
        self.btn_stop.configure(state="disabled")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="normal")
            
        messagebox.showinfo("Fim", "Processo concluído.")