import os
import shutil
import threading
import time
import tkinter as tk
from collections import Counter
from tkinter import filedialog, messagebox

import customtkinter as ctk


class FileTransferApp(ctk.CTk):
    def __init__(self):import os
import shutil
import threading
import time
from collections import Counter
from tkinter import filedialog, messagebox

import customtkinter as ctk


class FileTransferFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.source_path = ""
        self.dest_path = ""
        self.is_running = False
        self.is_paused = False
        self.stop_requested = False

        self.setup_ui()

    def setup_ui(self):
        # Configuração de Layout
        self.grid_columnconfigure(0, weight=1)
        self.configure(fg_color="transparent") # Deixa o fundo transparente para herdar da main

        # Título Interno
        self.label_title = ctk.CTkLabel(self, text="GESTÃO DE TRANSFERÊNCIA E AUDITORIA", font=("Arial", 20, "bold"))
        self.label_title.pack(pady=(10, 20))

        # Seletores de Caminho (Estilizados)
        frame_paths = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=10)
        frame_paths.pack(fill="x", padx=20, pady=10)

        self.btn_source = ctk.CTkButton(frame_paths, text="📁 ORIGEM", command=self.select_source, width=120, fg_color="#3d3d3d")
        self.btn_source.grid(row=0, column=0, padx=15, pady=10)
        self.lbl_source = ctk.CTkLabel(frame_paths, text="Nenhuma pasta selecionada", text_color="gray")
        self.lbl_source.grid(row=0, column=1, sticky="w")

        self.btn_dest = ctk.CTkButton(frame_paths, text="💾 DESTINO", command=self.select_dest, width=120, fg_color="#3d3d3d")
        self.btn_dest.grid(row=1, column=0, padx=15, pady=10)
        self.lbl_dest = ctk.CTkLabel(frame_paths, text="Nenhuma pasta selecionada", text_color="gray")
        self.lbl_dest.grid(row=1, column=1, sticky="w")

        # Terminal de Eventos (Estilo Matrix/Console)
        self.terminal = ctk.CTkTextbox(self, height=250, font=("Courier New", 12), fg_color="#1a1a1a", text_color="#2ecc71")
        self.terminal.pack(fill="both", padx=20, pady=10)

        # Barra de Progresso
        self.progress_bar = ctk.CTkProgressBar(self, width=800, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Aguardando Comando", font=("Arial", 12, "bold"))
        self.lbl_status.pack()

        self.lbl_eta = ctk.CTkLabel(self, text="Arquivos: 0/0 | Tempo: --:--:--")
        self.lbl_eta.pack()

        # Controles de Ação
        frame_controls = ctk.CTkFrame(self, fg_color="transparent")
        frame_controls.pack(pady=20)

        self.btn_start = ctk.CTkButton(frame_controls, text="INICIAR TRANSFERÊNCIA", fg_color="#2ecc71", hover_color="#27ae60", 
                                       command=lambda: self.launch("transfer"), width=220, height=40, font=("Arial", 12, "bold"))
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_audit = ctk.CTkButton(frame_controls, text="CONFERIR (AUDITORIA)", fg_color="#3498db", hover_color="#2980b9", 
                                       command=lambda: self.launch("audit"), width=220, height=40, font=("Arial", 12, "bold"))
        self.btn_audit.grid(row=0, column=1, padx=10)

        # Botões de Fluxo (Pausar/Parar)
        frame_flow = ctk.CTkFrame(self, fg_color="transparent")
        frame_flow.pack(pady=5)

        self.btn_pause = ctk.CTkButton(frame_flow, text="PAUSAR", fg_color="#f1c40f", text_color="black", 
                                       command=self.toggle_pause, width=100, state="disabled")
        self.btn_pause.grid(row=0, column=0, padx=5)

        self.btn_stop = ctk.CTkButton(frame_flow, text="PARAR", fg_color="#e74c3c", 
                                      command=self.stop_action, width=100, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=5)

    def log(self, message):
        self.terminal.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.terminal.see("end")

    def select_source(self):
        self.source_path = filedialog.askdirectory()
        if self.source_path: self.lbl_source.configure(text=self.source_path, text_color="white")

    def select_dest(self):
        self.dest_path = filedialog.askdirectory()
        if self.dest_path: self.lbl_dest.configure(text=self.dest_path, text_color="white")

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.configure(text="RETOMAR" if self.is_paused else "PAUSAR")

    def stop_action(self):
        self.stop_requested = True
        self.log("Solicitando parada segura...")

    def launch(self, mode):
        if not self.source_path or not self.dest_path:
            messagebox.showwarning("Erro", "Selecione origem e destino.")
            return
        
        self.is_running = True
        self.stop_requested = False
        self.is_paused = False
        self.btn_start.configure(state="disabled")
        self.btn_audit.configure(state="disabled")
        self.btn_pause.configure(state="normal")
        self.btn_stop.configure(state="normal")
        
        threading.Thread(target=self.process, args=(mode,), daemon=True).start()

    def process(self, mode):
        self.log(f"Iniciando modo: {mode.upper()}")
        stats = {
            "total_origem": 0, "transferidos": 0, "ja_existiam": 0, "erros": 0,
            "pastas": Counter(), "origem_por_pasta": Counter()
        }

        all_files = []
        for root, _, files in os.walk(self.source_path):
            if self.stop_requested: break
            folder_rel = os.path.relpath(root, self.source_path)
            stats["origem_por_pasta"][folder_rel] = len(files)
            for f in files:
                all_files.append(os.path.join(root, f))
        
        total = len(all_files)
        stats["total_origem"] = total

        for i, src in enumerate(all_files, 1):
            while self.is_paused: time.sleep(0.5)
            if self.stop_requested: break

            rel_path = os.path.relpath(src, self.source_path)
            folder_rel = os.path.dirname(rel_path)
            dst = os.path.join(self.dest_path, rel_path)
            
            try:
                exists = os.path.exists(dst)
                if mode == "transfer":
                    if exists: stats["ja_existiam"] += 1
                    else:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        stats["transferidos"] += 1
                        stats["pastas"][folder_rel] += 1
                elif mode == "audit":
                    if exists:
                        stats["ja_existiam"] += 1
                        stats["pastas"][folder_rel] += 1
                    else: self.log(f"FALTANDO: {rel_path}")
                
                self.progress_bar.set(i / total)
                self.lbl_eta.configure(text=f"Processando: {i}/{total}")
            except Exception as e:
                stats["erros"] += 1
                self.log(f"Erro: {e}")

        self.generate_report(mode, stats)

    def generate_report(self, mode, stats):
        self.log("\n" + "="*40)
        self.log(f"RELATÓRIO FINALIZADO")
        self.log(f"Total: {stats['total_origem']} | Erros: {stats['erros']}")
        self.log("="*40)
        
        self.btn_start.configure(state="normal")
        self.btn_audit.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        messagebox.showinfo("Fim do Processo", f"O processo de {mode} foi concluído com sucesso.")
        super().__init__()

        self.title("DOWNLOADER - Ultra Transfer & Auditor Pro")
        self.geometry("1000x800")
        
        self.source_path = ""
        self.dest_path = ""
        self.is_running = False
        self.is_paused = False
        self.stop_requested = False

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self.label_title = ctk.CTkLabel(self, text="Gestor de Transferência e Auditoria de Discos", font=("Arial", 22, "bold"))
        self.label_title.pack(pady=15)

        # Seletores de Caminho
        frame_paths = ctk.CTkFrame(self)
        frame_paths.pack(fill="x", padx=20, pady=10)

        self.btn_source = ctk.CTkButton(frame_paths, text="Origem", command=self.select_source, width=100)
        self.btn_source.grid(row=0, column=0, padx=10, pady=5)
        self.lbl_source = ctk.CTkLabel(frame_paths, text="Selecione a origem...", text_color="gray")
        self.lbl_source.grid(row=0, column=1, sticky="w")

        self.btn_dest = ctk.CTkButton(frame_paths, text="Destino", command=self.select_dest, width=100)
        self.btn_dest.grid(row=1, column=0, padx=10, pady=5)
        self.lbl_dest = ctk.CTkLabel(frame_paths, text="Selecione o destino...", text_color="gray")
        self.lbl_dest.grid(row=1, column=1, sticky="w")

        # Terminal de Eventos
        self.terminal = ctk.CTkTextbox(self, height=300, font=("Courier New", 12), fg_color="#1a1a1a", text_color="#00ff00")
        self.terminal.pack(fill="both", padx=20, pady=10)

        # Progresso
        self.progress_bar = ctk.CTkProgressBar(self, width=800)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Aguardando Comando", font=("Arial", 12, "bold"))
        self.lbl_status.pack()

        self.lbl_eta = ctk.CTkLabel(self, text="Arquivos: 0/0 | Tempo: --:--:--")
        self.lbl_eta.pack()

        # Controles Principais
        frame_main_controls = ctk.CTkFrame(self, fg_color="transparent")
        frame_main_controls.pack(pady=10)

        self.btn_start = ctk.CTkButton(frame_main_controls, text="INICIAR TRANSFERÊNCIA", fg_color="#2ecc71", hover_color="#27ae60", command=lambda: self.launch("transfer"), width=200)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_audit = ctk.CTkButton(frame_main_controls, text="CONFERIR (AUDITORIA)", fg_color="#3498db", hover_color="#2980b9", command=lambda: self.launch("audit"), width=200)
        self.btn_audit.grid(row=0, column=1, padx=10)

        # Controles de Fluxo
        frame_flow = ctk.CTkFrame(self, fg_color="transparent")
        frame_flow.pack(pady=5)

        self.btn_pause = ctk.CTkButton(frame_flow, text="PAUSAR", fg_color="#f1c40f", command=self.toggle_pause, width=120, state="disabled")
        self.btn_pause.grid(row=0, column=0, padx=5)

        self.btn_stop = ctk.CTkButton(frame_flow, text="PARAR", fg_color="#e74c3c", command=self.stop_action, width=120, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=5)

    def log(self, message):
        self.terminal.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.terminal.see("end")

    def select_source(self):
        self.source_path = filedialog.askdirectory()
        if self.source_path: self.lbl_source.configure(text=self.source_path, text_color="white")

    def select_dest(self):
        self.dest_path = filedialog.askdirectory()
        if self.dest_path: self.lbl_dest.configure(text=self.dest_path, text_color="white")

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.configure(text="RETOMAR" if self.is_paused else "PAUSAR")

    def stop_action(self):
        self.stop_requested = True
        self.log("Solicitando parada segura...")

    def launch(self, mode):
        if not self.source_path or not self.dest_path:
            messagebox.showwarning("Erro", "Selecione origem e destino.")
            return
        
        self.is_running = True
        self.stop_requested = False
        self.is_paused = False
        self.btn_start.configure(state="disabled")
        self.btn_audit.configure(state="disabled")
        self.btn_pause.configure(state="normal")
        self.btn_stop.configure(state="normal")
        
        threading.Thread(target=self.process, args=(mode,), daemon=True).start()

    def process(self, mode):
        self.log(f"Iniciando modo: {mode.upper()}")
        
        # Estatísticas detalhadas
        stats = {
            "total_origem": 0,
            "transferidos": 0,
            "ja_existiam": 0,
            "erros": 0,
            "pastas": Counter(), # Quantidade transferida/conferida por pasta
            "origem_por_pasta": Counter() # Quantidade total na origem por pasta
        }

        # Mapeamento
        all_files = []
        for root, _, files in os.walk(self.source_path):
            if self.stop_requested: break
            folder_rel = os.path.relpath(root, self.source_path)
            stats["origem_por_pasta"][folder_rel] = len(files)
            for f in files:
                all_files.append(os.path.join(root, f))
        
        total = len(all_files)
        stats["total_origem"] = total
        start_time = time.time()

        for i, src in enumerate(all_files, 1):
            while self.is_paused: time.sleep(0.5)
            if self.stop_requested: break

            rel_path = os.path.relpath(src, self.source_path)
            folder_rel = os.path.dirname(rel_path)
            dst = os.path.join(self.dest_path, rel_path)
            
            try:
                exists = os.path.exists(dst)
                
                if mode == "transfer":
                    if exists:
                        stats["ja_existiam"] += 1
                    else:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        stats["transferidos"] += 1
                        stats["pastas"][folder_rel] += 1
                
                elif mode == "audit":
                    if exists:
                        stats["ja_existiam"] += 1
                        stats["pastas"][folder_rel] += 1
                    else:
                        self.log(f"FALTANDO: {rel_path}")
                
                # Update UI
                self.progress_bar.set(i / total)
                self.lbl_eta.configure(text=f"Processando: {i}/{total}")

            except Exception as e:
                stats["erros"] += 1
                self.log(f"Erro: {e}")

        self.generate_report(mode, stats)

    def generate_report(self, mode, stats):
        self.log("\n" + "="*40)
        self.log(f"RELATÓRIO DE {mode.upper()}")
        self.log("="*40)
        self.log(f"Total na Origem: {stats['total_origem']}")
        self.log(f"Já existiam no Destino: {stats['ja_existiam']}")
        
        if mode == "transfer":
            self.log(f"Efetivamente Transferidos: {stats['transferidos']}")
        else:
            self.log(f"Confirmados no Destino: {stats['ja_existiam']}")
            self.log(f"Ausentes no Destino: {stats['total_origem'] - stats['ja_existiam']}")
        
        self.log(f"Falhas/Erros: {stats['erros']}")
        
        self.log("\nDETALHAMENTO POR PASTA (TOP 20):")
        self.log(f"{'Pasta':<30} | {'Origem':<8} | {'Sincronizado':<8}")
        self.log("-" * 55)
        
        # Ordena pelas pastas com mais arquivos na origem
        for folder, total_orig in stats["origem_por_pasta"].most_common(20):
            sync_count = stats["pastas"][folder] if mode == "transfer" else stats["ja_existiam"]
            # No modo auditoria, mostramos quantos dos arquivos daquela pasta específica foram achados
            self.log(f"{folder[:30]:<30} | {total_orig:<8} | {stats['pastas'][folder]:<8}")

        self.log("="*40)
        
        self.btn_start.configure(state="normal")
        self.btn_audit.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        messagebox.showinfo("Fim do Processo", f"O relatório de {mode} foi gerado no terminal.")

if __name__ == "__main__":
    app = FileTransferApp()
    app.mainloop()