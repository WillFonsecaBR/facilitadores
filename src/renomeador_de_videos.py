"""
FERRAMENTA: RENOMEADOR DE VÍDEOS (FACILITADORES) - VERSÃO ULTRA VELOCIDADE 4.1
MELHORIAS DE PERFORMANCE E EMBARALHAMENTO:
1. Prefixo de 15 Dígitos: Sequência numérica inicial expandida para exatamente 15 caracteres.
2. Embaralhamento Total (Anti-Vizinhos): Utiliza SHA-256 com efeito avalanche para garantir que
   arquivos processados em sequência tenham prefixos completamente diferentes, impedindo que fiquem próximos.
3. Polling Ativo: UI consome dados da memória a cada 100ms, garantindo fluidez sem travar a interface.
4. Resolução Estática: Substituído a leitura dinâmica de resolução por "VIDEO" estático, garantindo velocidade máxima.
5. Preservação Total: Nenhuma mudança visual ou na lógica de renomeação.
"""
import hashlib
import os
import random
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    import cv2
except ImportError:
    cv2 = None

class RenomeadorFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.allowed_image_ext = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"]
        self.allowed_video_ext = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]
        self.error_log_name = "errors_renomeador.log"
        self.processando = False
        self.pausado = False
        self.stop_request = False
        self.arquivos_total = 0
        self.arquivos_processados = 0
        self.arquivos_falhos = 0
        self.inicio_tempo = 0
        
        # Variáveis de controle de UI (Thread-Safe)
        self.ui_progresso = 0.0
        self.ui_stats_text = "Arquivos: 0/0 | Erros: 0 | Tempo: 00:00 | Restante: ~00:00"
        self.ui_status_text = "Status: Aguardando Comando"
        self.log_queue = []
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")
        
        # --- Seleção de Pasta ---
        self.folder_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        self.folder_frame.pack(fill="x", padx=20, pady=(10, 10))
        
        self.entry_path = ctk.CTkEntry(self.folder_frame, placeholder_text="Selecione a pasta raiz...", height=35, fg_color="#0f0f0f")
        self.entry_path.pack(side="left", fill="x", expand=True, padx=15, pady=15)
        
        self.btn_browse = ctk.CTkButton(self.folder_frame, text="📁 Selecionar Pasta", width=140, fg_color="#3d3d3d", command=self.selecionar_pasta)
        self.btn_browse.pack(side="right", padx=15)
        
        # --- Terminal de Log ---
        self.terminal = ctk.CTkTextbox(self, height=280, fg_color="#000000", text_color="#2ecc71", font=("Consolas", 12))
        self.terminal.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- Status e Progresso ---
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20, pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=800, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=5)
        
        self.lbl_stats = ctk.CTkLabel(self.status_frame, text="Arquivos: 0/0 | Erros: 0 | Tempo: 00:00 | Restante: ~00:00", font=("Segoe UI", 11, "bold"))
        self.lbl_stats.pack(pady=5)
        
        self.lbl_status = ctk.CTkLabel(self, text="Status: Aguardando Comando", font=("Segoe UI", 12))
        self.lbl_status.pack(pady=(0, 10))
        
        # --- Controles ---
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(pady=10)
        
        self.btn_start = ctk.CTkButton(self.control_frame, text="▶ INICIAR PROCESSO", fg_color="#2ecc71", hover_color="#27ae60", 
                                       width=220, height=40, font=("Segoe UI", 12, "bold"), command=self.iniciar)
        self.btn_start.grid(row=0, column=0, padx=10)
        
        self.btn_pause = ctk.CTkButton(self.control_frame, text="PAUSAR", state="disabled", width=120, command=self.alternar_pausa)
        self.btn_pause.grid(row=0, column=1, padx=5)
        
        self.btn_stop = ctk.CTkButton(self.control_frame, text="PARAR", fg_color="#e74c3c", width=120, state="disabled", command=self.parar)
        self.btn_stop.grid(row=0, column=2, padx=5)

    def log(self, mensagem):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.append(f"[{timestamp}] {mensagem}")

    def atualizar_interface_periodico(self):
        """Atualiza todos os elementos visuais de forma segura na Thread Principal."""
        if self.processando:
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

    def selecionar_pasta(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, pasta)

    def alternar_pausa(self):
        self.pausado = not self.pausado
        self.btn_pause.configure(text="RETOMAR" if self.pausado else "PAUSAR")

    def parar(self):
        self.stop_request = True
        self.log("Solicitando parada segura...")

    def iniciar(self):
        pasta = self.entry_path.get()
        if not pasta or not os.path.exists(pasta):
            messagebox.showwarning("Aviso", "Selecione uma pasta válida.")
            return
        self.terminal.delete("1.0", "end")
        self.progress_bar.set(0)
        self.ui_progresso = 0.0
        self.ui_stats_text = "Arquivos: 0/0 | Erros: 0 | Tempo: 00:00 | Restante: ~00:00"
        self.ui_status_text = "Status: Iniciando..."
        self.arquivos_processados = 0
        self.arquivos_falhos = 0
        self.processando = True
        self.pausado = False
        self.stop_request = False
        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal")
        self.btn_stop.configure(state="normal")
        self.log_queue = []
        self.atualizar_interface_periodico()
        threading.Thread(target=self.worker, args=(pasta,), daemon=True).start()

    def worker(self, root_path_str):
        self.inicio_tempo = time.time()
        self.log("Iniciando varredura profunda de diretórios...")
        arquivos = []
        count = 0
        for root, dirs, files in os.walk(root_path_str):
            if self.stop_request: break
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.allowed_image_ext or ext in self.allowed_video_ext:
                    if not file.startswith(".") and not file.startswith("._"):
                        arquivos.append(os.path.join(root, file))
                        count += 1
                        if count % 1000 == 0:
                            self.ui_status_text = f"Varrendo: {count} arquivos encontrados..."
        self.arquivos_total = len(arquivos)
        if self.arquivos_total == 0:
            self.log("Nenhum arquivo encontrado.")
            self.finalizar()
            return
        self.log(f"Varredura concluída: {self.arquivos_total} arquivos na fila.")
        for i, arq_path in enumerate(arquivos, 1):
            while self.pausado and not self.stop_request:
                time.sleep(0.1)
            if self.stop_request:
                self.log("Processamento interrompido.")
                break
            try:
                arq_obj = Path(arq_path)
                novo_nome = self.processar_arquivo(arq_obj, Path(root_path_str), i)
                self.arquivos_processados += 1
                self.log(f"OK: {os.path.basename(arq_path)} -> {novo_nome}")
            except Exception as e:
                self.arquivos_falhos += 1
                self.log(f"ERRO em {os.path.basename(arq_path)}: {e}")
            # Updates UI parameters in memory
            self.ui_progresso = i / self.arquivos_total
            elapsed = time.time() - self.inicio_tempo
            tempo_decorrido = time.strftime("%M:%S", time.gmtime(elapsed))
            velocidade = i / elapsed if elapsed > 0 else 0
            restante = (self.arquivos_total - i) / velocidade if velocidade > 0 else 0
            tempo_restante = time.strftime("%M:%S", time.gmtime(restante))
            self.ui_stats_text = f"Arquivos: {i}/{self.arquivos_total} | Erros: {self.arquivos_falhos} | Tempo: {tempo_decorrido} | Restante: ~{tempo_restante}"
            self.ui_status_text = f"Processando: {os.path.basename(arq_path)}"
        self.finalizar()

    def processar_arquivo(self, arq, root_path, num):
        ext = arq.suffix.lower()
        
        # Define a resolução estática como "VIDEO" ou "IMAGE" sem ler metadados
        resolucao = "VIDEO" if ext in self.allowed_video_ext else "IMAGE"
        
        stat_info = arq.stat()
        data = datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y%m%d")
        hash_str = self.calcular_hash_otimizado(arq, stat_info.st_size)
        
        # Prefixo de 15 dígitos com SHA-256 (Efeito Avalanche)
        semente = f"{arq.name}_{num}_{time.time()}_{random.random()}"
        prefixo_num = int(hashlib.sha256(semente.encode()).hexdigest(), 16) % 10**15
        prefixo = f"{prefixo_num:015d}"
        categoria_raiz = root_path.name.upper()
        
        novo_nome = f"{prefixo}_{categoria_raiz}_{resolucao}_{data}_{num:04d}_{hash_str}{ext}"
        os.rename(str(arq), str(arq.parent / novo_nome))
        return novo_nome

    def calcular_hash_otimizado(self, arq, size):
        h = hashlib.md5()
        try:
            with open(arq, "rb") as f:
                if size > 16384:
                    h.update(f.read(8192))
                    f.seek(-8192, 2)
                    h.update(f.read(8192))
                else:
                    h.update(f.read())
        except: 
            pass
        return h.hexdigest()[:10].upper()

    def obter_resolucao(self, arq):
        # Mantido apenas por compatibilidade de assinatura, mas não é mais invocado
        try:
            cap = cv2.VideoCapture(str(arq))
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            return f"{w}X{h}" if w > 0 else "VIDEO"
        except: 
            return "VIDEO"

    def finalizar(self):
        self.after(0, self.finalizar_main_thread)

    def finalizar_main_thread(self):
        self.processando = False
        if self.log_queue:
            self.terminal.insert("end", "\n".join(self.log_queue) + "\n")
            self.log_queue = []
            self.terminal.see("end")
        self.progress_bar.set(self.ui_progresso)
        self.lbl_stats.configure(text=self.ui_stats_text)
        self.lbl_status.configure(text="Concluído." if not self.stop_request else "Interrompido.")
        self.btn_start.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        messagebox.showinfo("Fim", "Processo finalizado.")