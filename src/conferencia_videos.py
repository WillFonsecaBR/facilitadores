"""
FERRAMENTA: CONFERÊNCIA DE VÍDEOS (FACILITADORES)
LÓGICA:
1. EXTRAIR FRAMES: Captura um frame específico definido pelo usuário (em segundos).
2. SEPARAÇÃO: Move vídeos da raiz para '00_COM_MD' baseado nas imagens selecionadas.
3. PERFORMANCE: Extração via Seek (OpenCV) para processar milhares de arquivos.
"""

import os
import re
import shutil
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:
    import cv2
except ImportError:
    cv2 = None

class ConferenciaVideosFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.allowed_video_ext = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]
        self.root_folder = ""
        self.is_running = False
        self.stop_requested = False
        self.start_time = 0
        self.error_count = 0
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Título
        ctk.CTkLabel(self, text="CONFERÊNCIA E SEPARAÇÃO DE VÍDEOS", 
                     font=("Segoe UI", 20, "bold")).pack(pady=(10, 10))

        # Configurações e Pasta
        top_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        top_frame.pack(fill="x", padx=20, pady=10)

        self.btn_folder = ctk.CTkButton(top_frame, text="📁 SELECIONAR PASTA", 
                                        command=self.select_folder, fg_color="#3d3d3d", width=160)
        self.btn_folder.grid(row=0, column=0, padx=15, pady=15)
        
        self.lbl_folder = ctk.CTkLabel(top_frame, text="Nenhum diretório selecionado", text_color="gray")
        self.lbl_folder.grid(row=0, column=1, sticky="w", padx=5)

        # CAMPO DE TEMPO DO FRAME (NOVO)
        time_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        time_frame.grid(row=0, column=2, padx=20)
        
        ctk.CTkLabel(time_frame, text="Capturar no segundo:").pack(side="left", padx=5)
        self.entry_time = ctk.CTkEntry(time_frame, width=60, placeholder_text="1")
        self.entry_time.insert(0, "1") # Padrão: 1 segundo
        self.entry_time.pack(side="left")

        # Terminal de Logs
        self.terminal = ctk.CTkTextbox(self, height=300, font=("Courier New", 12), 
                                       fg_color="#000000", text_color="#2ecc71")
        self.terminal.pack(fill="both", padx=20, pady=10)

        # Barra de Status
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20)
        self.status_frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.lbl_files = ctk.CTkLabel(self.status_frame, text="Processado: 0/0")
        self.lbl_files.grid(row=0, column=0)

        self.lbl_time = ctk.CTkLabel(self.status_frame, text="Tempo: 00:00:00")
        self.lbl_time.grid(row=0, column=1)

        self.lbl_eta = ctk.CTkLabel(self.status_frame, text="Restante: ~00:00")
        self.lbl_eta.grid(row=0, column=2)

        self.lbl_errors = ctk.CTkLabel(self.status_frame, text="Erros: 0", text_color="#e74c3c")
        self.lbl_errors.grid(row=0, column=3)

        self.progress_bar = ctk.CTkProgressBar(self, width=800, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=15)

        # Controles
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)

        self.btn_frames = ctk.CTkButton(self.ctrl_frame, text="1. GERAR FRAMES", fg_color="#3498db", 
                                        width=200, height=40, font=("Segoe UI", 12, "bold"), 
                                        command=lambda: self.start_task("frames"))
        self.btn_frames.grid(row=0, column=0, padx=10)

        self.btn_separar = ctk.CTkButton(self.ctrl_frame, text="2. SEPARAR VÍDEOS", fg_color="#2ecc71", 
                                         width=200, height=40, font=("Segoe UI", 12, "bold"), 
                                         command=lambda: self.start_task("separar"))
        self.btn_separar.grid(row=0, column=1, padx=10)

        self.btn_stop = ctk.CTkButton(self.ctrl_frame, text="PARAR", fg_color="#e74c3c", 
                                      width=120, height=40, state="disabled", command=self.stop_process)
        self.btn_stop.grid(row=0, column=2, padx=10)

    def log(self, msg):
        self.terminal.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.terminal.see("end")

    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.root_folder = Path(path)
            self.lbl_folder.configure(text=str(self.root_folder), text_color="white")

    def stop_process(self):
        self.stop_requested = True
        self.log("Solicitando parada segura...")

    def lock_ui(self, lock=True):
        state = "disabled" if lock else "normal"
        self.btn_frames.configure(state=state)
        self.btn_separar.configure(state=state)
        self.btn_folder.configure(state=state)
        self.entry_time.configure(state=state)
        self.btn_stop.configure(state="normal" if lock else "disabled")
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state=state)

    def start_task(self, task_type):
        if not self.root_folder:
            messagebox.showwarning("Aviso", "Selecione o diretório primeiro.")
            return
        
        # Validação do tempo do frame
        try:
            self.target_second = float(self.entry_time.get().replace(",", "."))
            if self.target_second < 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Aviso", "Digite um tempo válido (ex: 1 ou 2.5)")
            return

        self.terminal.delete("1.0", "end")
        self.is_running = True
        self.stop_requested = False
        self.error_count = 0
        self.start_time = time.time()
        self.lock_ui(True)
        
        if task_type == "frames":
            threading.Thread(target=self.worker_frames, daemon=True).start()
        else:
            threading.Thread(target=self.worker_separar, daemon=True).start()
            
        threading.Thread(target=self.update_timer, daemon=True).start()

    def update_timer(self):
        while self.is_running:
            elapsed = time.time() - self.start_time
            self.lbl_time.configure(text=f"Tempo: {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
            time.sleep(1)

    def worker_frames(self):
        self.log(f"Iniciando extração no segundo {self.target_second}...")
        conf_dir = self.root_folder / "00_CONFERENCIA"
        md_dir = conf_dir / "00_COM_MD"
        fin_dir = conf_dir / "00_FINALIZADO"
        
        for d in [conf_dir, md_dir, fin_dir]:
            d.mkdir(parents=True, exist_ok=True)

        videos = [f for f in self.root_folder.iterdir() if f.suffix.lower() in self.allowed_video_ext]
        total = len(videos)

        if total == 0:
            self.log("Nenhum vídeo encontrado.")
            self.finish_task(0)
            return

        for i, video_path in enumerate(videos, 1):
            if self.stop_requested: break
            
            try:
                cap = cv2.VideoCapture(str(video_path))
                # Pula para o segundo exato definido pelo usuário
                cap.set(cv2.CAP_PROP_POS_MSEC, self.target_second * 1000) 
                success, frame = cap.read()
                
                if success:
                    img_name = video_path.stem + ".jpg"
                    cv2.imwrite(str(conf_dir / img_name), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    self.log(f"OK: {video_path.name}")
                else:
                    self.error_count += 1
                    self.log(f"ERRO: Falha ao capturar frame de {video_path.name}")
                cap.release()
            except Exception as e:
                self.error_count += 1
                self.log(f"FALHA: {video_path.name} | {e}")

            self.update_status(i, total)

        self.finish_task(total, "Geração de Frames")

    def worker_separar(self):
        self.log("Iniciando separação automática...")
        source_img_dir = self.root_folder / "00_CONFERENCIA" / "00_COM_MD"
        dest_video_dir = self.root_folder / "00_COM_MD"
        
        if not source_img_dir.exists():
            self.log(f"ERRO: Pasta de conferência não encontrada.")
            self.finish_task(0)
            return

        dest_video_dir.mkdir(parents=True, exist_ok=True)
        imagens_md = [f.stem for f in source_img_dir.iterdir() if f.suffix.lower() in [".jpg", ".jpeg", ".png"]]
        total = len(imagens_md)

        if total == 0:
            self.log("Nenhuma imagem para processar em 00_COM_MD.")
            self.finish_task(0)
            return

        movidos = 0
        for i, nome_base in enumerate(imagens_md, 1):
            if self.stop_requested: break
            
            encontrado = False
            for ext in self.allowed_video_ext:
                video_origem = self.root_folder / (nome_base + ext)
                if video_origem.exists():
                    try:
                        shutil.move(str(video_origem), str(dest_video_dir / video_origem.name))
                        self.log(f"MOVIDO: {video_origem.name}")
                        movidos += 1
                        encontrado = True
                        break
                    except Exception as e:
                        self.error_count += 1
                        self.log(f"ERRO ao mover {video_origem.name}: {e}")
            
            if not encontrado:
                self.log(f"AVISO: Vídeo '{nome_base}' não encontrado na raiz.")

            self.update_status(i, total)

        self.finish_task(movidos, "Separação de Vídeos")

    def update_status(self, i, total):
        prog = i / total
        self.progress_bar.set(prog)
        self.lbl_files.configure(text=f"Processado: {i}/{total}")
        self.lbl_errors.configure(text=f"Erros: {self.error_count}")
        
        elapsed = time.time() - self.start_time
        avg = elapsed / i if i > 0 else 0
        eta = avg * (total - i)
        self.lbl_eta.configure(text=f"Restante: ~{time.strftime('%M:%S', time.gmtime(eta))}")

    def finish_task(self, total, nome_tarefa="Processo"):
        self.is_running = False
        self.lock_ui(False)
        self.log("\n" + "="*40)
        self.log(f"RELATÓRIO: {nome_tarefa}")
        self.log(f"Total: {total} | Erros: {self.error_count}")
        self.log(f"Duração: {time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))}")
        self.log("="*40)
        messagebox.showinfo("Concluído", f"{nome_tarefa} finalizado.")