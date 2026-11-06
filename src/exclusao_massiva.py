"""
FERRAMENTA: EXCLUSÃO MASSIVA DE DADOS (FACILITADORES) - VERSÃO INDUSTRIAL 1.0
LÓGICA:
1. VARREDURA INVERSA: Usa os.walk(topdown=False) para listar e apagar arquivos antes de suas pastas pai.
2. EXCLUSÃO ATÔMICA: Utiliza os.remove() e os.rmdir() nativos do C para velocidade máxima de I/O.
3. SEGURANÇA: Exige dupla confirmação por pop-up antes de iniciar qualquer destruição de dados.
4. MONITORAMENTO PRO (THREAD-SAFE): Interface atualizada via polling a cada 100ms, sem travar o app.
"""

import os
import shutil
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk


class ExclusaoMassivaFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.is_running = False
        self.pausado = False
        self.stop_requested = False
        self.start_time = 0
        self.root_dir = None
        
        # Variáveis de controle de UI (Thread-Safe)
        self.ui_progresso = 0.0
        self.ui_stats_text = "Apagados: 0 | Pastas Removidas: 0 | Erros: 0"
        self.ui_status_text = "Status: Aguardando Comando"
        self.log_queue = []
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Título com Alerta de Perigo
        ctk.CTkLabel(self, text="❌ EXCLUSÃO MASSIVA DE DADOS", 
                     font=("Segoe UI", 20, "bold"), text_color="#e74c3c").pack(pady=(10, 20))

        # Seleção de Pasta Alvo
        frame_path = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        frame_path.pack(fill="x", padx=20, pady=10)

        self.btn_folder = ctk.CTkButton(frame_path, text="📁 SELECIONAR PASTA ALVO", 
                                        command=self.select_folder, fg_color="#3d3d3d")
        self.btn_folder.grid(row=0, column=0, padx=15, pady=15)
        
        self.lbl_folder = ctk.CTkLabel(frame_path, text="Nenhum diretório selecionado (CUIDADO!)", text_color="gray")
        self.lbl_folder.grid(row=0, column=1, sticky="w")

        # Terminal de Logs (Estilo Console de Destruição)
        self.terminal = ctk.CTkTextbox(self, height=300, font=("Courier New", 12), 
                                       fg_color="#000000", text_color="#e74c3c")
        self.terminal.pack(fill="both", padx=20, pady=10)

        # Painel de Status Detalhado
        self.status_container = ctk.CTkFrame(self, fg_color="transparent")
        self.status_container.pack(fill="x", padx=20)
        self.status_container.grid_columnconfigure((0,1,2), weight=1)

        self.lbl_stats = ctk.CTkLabel(self.status_container, text="Apagados: 0 | Pastas Removidas: 0 | Erros: 0", font=("Segoe UI", 11, "bold"))
        self.lbl_stats.grid(row=0, column=0, sticky="w")

        self.lbl_timer = ctk.CTkLabel(self.status_container, text="Tempo Decorrido: 00:00", font=("Segoe UI", 11))
        self.lbl_timer.grid(row=0, column=1)

        self.lbl_status = ctk.CTkLabel(self.status_container, text="Status: Aguardando", font=("Segoe UI", 11, "bold"))
        self.lbl_status.grid(row=0, column=2, sticky="e")

        # Barra de Progresso (Vermelha para indicar perigo)
        self.progress_bar = ctk.CTkProgressBar(self, width=800, progress_color="#e74c3c")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(5, 20), padx=20)

        # Controles
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.ctrl_frame, text="💥 DESTRUIR TUDO DEFINITIVAMENTE", fg_color="#e74c3c", 
                                       hover_color="#c0392b", width=260, height=45, 
                                       font=("Segoe UI", 12, "bold"), command=self.iniciar)
        self.btn_start.grid(row=0, column=0, padx=5)

        self.btn_pause = ctk.CTkButton(self.ctrl_frame, text="PAUSAR", state="disabled", 
                                       width=120, height=45, command=self.alternar_pausa)
        self.btn_pause.grid(row=0, column=1, padx=5)

        self.btn_stop = ctk.CTkButton(self.ctrl_frame, text="PARAR", fg_color="#7f8c8d", 
                                      width=120, height=45, state="disabled", command=self.stop)
        self.btn_stop.grid(row=0, column=2, padx=5)

    def log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        self.log_queue.append(f"[{timestamp}] {msg}")

    def atualizar_interface_periodico(self):
        """Descarrega logs e atualiza a interface a cada 100ms na Thread Principal."""
        if self.is_running:
            if self.log_queue:
                lote = self.log_queue[:]
                self.log_queue = self.log_queue[len(lote):]
                self.terminal.insert("end", "\n".join(lote) + "\n")
                
                # Limita linhas no terminal para evitar lentidão
                linhas_total = float(self.terminal.index('end-1c').split('.')[0])
                if linhas_total > 1000:
                    self.terminal.delete("1.0", f"{int(linhas_total - 1000)}.0")
                self.terminal.see("end")
            
            self.progress_bar.set(self.ui_progresso)
            self.lbl_stats.configure(text=self.ui_stats_text)
            self.lbl_status.configure(text=self.ui_status_text)
            
            elapsed = time.time() - self.start_time
            self.lbl_timer.configure(text=f"Tempo Decorrido: {time.strftime('%M:%S', time.gmtime(elapsed))}")
            
            self.after(100, self.atualizar_interface_periodico)

    def select_folder(self):
        path = filedialog.askdirectory(title="SELECIONE A PASTA QUE SERÁ TOTALMENTE APAGADA")
        if path:
            self.root_dir = Path(path)
            self.lbl_folder.configure(text=str(self.root_dir), text_color="#e74c3c")

    def alternar_pausa(self):
        self.pausado = not self.pausado
        self.btn_pause.configure(text="RETOMAR" if self.pausado else "PAUSAR")
        if self.pausado:
            self.log("Exclusão pausada pelo usuário.")
        else:
            self.log("Exclusão retomada.")

    def stop(self):
        self.stop_requested = True
        self.log("Solicitando parada de emergência...")

    def iniciar(self):
        if not self.root_dir or not self.root_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta válida para exclusão.")
            return

        # Dupla confirmação de segurança
        confirma_1 = messagebox.askyesno("PERIGO EXTREMO", f"Você tem certeza absoluta que deseja apagar TODOS os arquivos e pastas dentro de:\n\n{self.root_dir}\n\nEsta ação é irreversível!")
        if not confirma_1:
            return

        confirma_2 = messagebox.askyesno("CONFIRMAÇÃO FINAL", "ÚLTIMO AVISO: Os dados não irão para a lixeira. Eles serão deletados permanentemente do disco. Deseja prosseguir?")
        if not confirma_2:
            return

        self.is_running = True
        self.pausado = False
        self.stop_requested = False
        
        self.btn_start.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
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
            self.log("Iniciando mapeamento completo de arquivos e diretórios...")
            self.ui_status_text = "Mapeando..."
            
            itens_para_deletar = []
            root_str = str(self.root_dir)
            
            # Varredura reversa de alta velocidade (topdown=False)
            for root, dirs, files in os.walk(root_str, topdown=False):
                if self.stop_requested: break
                for file in files:
                    itens_para_deletar.append((os.path.join(root, file), "arquivo"))
                for directory in dirs:
                    itens_para_deletar.append((os.path.join(root, directory), "pasta"))

            total_itens = len(itens_para_deletar)
            self.log(f"Mapeamento concluído! Encontrados {total_itens} itens para destruição.")

            if total_itens == 0:
                self.log("A pasta já está completamente vazia.")
                return

            apagados_arquivos = 0
            apagados_pastas = 0
            erros = 0

            for idx, (caminho, tipo) in enumerate(itens_para_deletar, 1):
                # Lógica de Pausa
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)
                
                if self.stop_requested: 
                    self.log("Operação interrompida pelo usuário de forma segura.")
                    break

                try:
                    if tipo == "arquivo":
                        os.remove(caminho)
                        apagados_arquivos += 1
                        self.log(f"DELETADO: {os.path.basename(caminho)}")
                    else:
                        os.rmdir(caminho)
                        apagados_pastas += 1
                        self.log(f"PASTA REMOVIDA: {os.path.basename(caminho)}")
                except Exception as e:
                    erros += 1
                    self.log(f"ERRO ao deletar {os.path.basename(caminho)}: {e}")

                # Atualiza variáveis na memória (Thread-Safe)
                self.ui_progresso = idx / total_itens
                self.ui_stats_text = f"Apagados: {apagados_arquivos} | Pastas Removidas: {apagados_pastas} | Erros: {erros}"
                self.ui_status_text = f"Destruindo: {idx}/{total_itens}"

            # Relatório Final
            duracao = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
            self.log("\n" + "="*40)
            self.log("RELATÓRIO DE EXCLUSÃO MASSIVA")
            self.log(f"Duração do Processo: {duracao}")
            self.log(f"Arquivos Apagados: {apagados_arquivos}")
            self.log(f"Pastas Removidas: {apagados_pastas}")
            self.log(f"Falhas/Erros: {erros}")
            self.log("="*40)

        except Exception as e:
            self.log(f"ERRO CRÍTICO NO PROCESSO: {e}")
        finally:
            self.finalizar()

    def finalizar(self):
        self.after(0, self.finalizar_main_thread)

    def finalizar_main_thread(self):
        self.is_running = False
        
        # Descarrega logs finais
        if self.log_queue:
            self.terminal.insert("end", "\n".join(self.log_queue) + "\n")
            self.log_queue = []
            self.terminal.see("end")
            
        self.progress_bar.set(self.ui_progresso)
        self.lbl_stats.configure(text=self.ui_stats_text)
        self.lbl_status.configure(text="Concluído" if not self.stop_requested else "Interrompido")
        
        self.btn_start.configure(state="normal")
        self.btn_folder.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="PAUSAR")
        self.btn_stop.configure(state="disabled")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="normal")
            
        messagebox.showinfo("Fim", "Processo de exclusão massiva concluído.")