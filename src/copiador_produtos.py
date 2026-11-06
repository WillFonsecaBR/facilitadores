"""
FERRAMENTA: COPIADOR DE PRODUTOS (FACILITADORES) - VERSÃO ULTRA PERFORMANCE 1.3
LÓGICA:
1. VARREDURA: Identifica todas as pastas que contêm vídeos diretamente ou em subpastas.
2. SELEÇÃO ALEATÓRIA: Seleciona exatamente 20 vídeos aleatórios de cada pasta de pack.
3. MAPEAMENTO DE NICHOS: Identifica o Nicho (1º nível abaixo da raiz) e a pasta do Pack,
   ignorando qualquer pasta intermediária e recriando a estrutura dentro de '00_PRODUTOS'.
4. CÓPIA EM BUFFER (STREAMING): Copia os arquivos em blocos de 1MB para permitir pausa e parada instantânea.
5. GERAÇÃO DE ÍNDICES TXT: Cria automaticamente um arquivo "[NOME_DO_NICHO].txt" dentro de cada pasta 
   de nicho listando todos os packs contidos nela.
6. TRAVAS DE SEGURANÇA MÁXIMA (NO-ESCAPE):
   - Bloqueia o fechamento da janela (Alt+F4 / Botão X) enquanto o processo estiver rodando.
   - Desabilita recursivamente todos os botões e menus de navegação externos ao frame.
7. INTERFACE THREAD-SAFE: Atualização de progresso e logs via polling a cada 100ms para evitar travamentos.
"""

import os
import random
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk


class CopiadorProdutosFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.allowed_video_ext = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]
        self.qty_to_copy = 20  # Configurado para exatamente 20 vídeos aleatórios
        
        self.is_running = False
        self.pausado = False
        self.stop_requested = False
        self.start_time = 0
        self.root_dir = None
        self.dest_dir = None
        self.root_window = None
        self.original_close_handler = None
        self.current_process = None
        
        # Variáveis de controle de UI (Thread-Safe)
        self.ui_progresso = 0.0
        self.ui_stats_text = "Arquivos Copiados: 0/0 | Tempo: 00:00 | Restante: ~00:00"
        self.ui_status_text = "Status: Aguardando Comando"
        self.log_queue = []
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Título
        ctk.CTkLabel(self, text="COPIADOR DE PRODUTOS (20 VÍDEOS ALEATÓRIOS)", 
                     font=("Segoe UI", 20, "bold")).pack(pady=(10, 15))

        # Painel de Configurações
        config_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        config_frame.pack(fill="x", padx=20, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        # Seleção de Pasta Raiz (Origem)
        ctk.CTkLabel(config_frame, text="Pasta Raiz:", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        folder_origin_subframe = ctk.CTkFrame(config_frame, fg_color="transparent")
        folder_origin_subframe.grid(row=0, column=1, padx=15, pady=15, sticky="ew")
        
        self.btn_origin = ctk.CTkButton(folder_origin_subframe, text="📁 SELECIONAR PASTA", 
                                        command=self.select_origin_folder, fg_color="#3d3d3d", width=160)
        self.btn_origin.pack(side="left")
        self.lbl_origin = ctk.CTkLabel(folder_origin_subframe, text="Selecione a pasta raiz contendo as subpastas de nicho", text_color="gray")
        self.lbl_origin.pack(side="left", padx=10)

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

        self.lbl_stats = ctk.CTkLabel(self.status_frame, text="Arquivos Copiados: 0/0 | Tempo: 00:00 | Restante: ~00:00", 
                                      font=("Segoe UI", 11, "bold"))
        self.lbl_stats.pack(pady=2)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Aguardando Comando", font=("Segoe UI", 12))
        self.lbl_status.pack(pady=(0, 10))

        # Controles
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.ctrl_frame, text="▶ INICIAR CÓPIA", fg_color="#3498db", 
                                       hover_color="#2980b9", width=220, height=45, 
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
                
                # Limita tamanho do terminal para evitar lentidão
                linhas_total = float(self.terminal.index('end-1c').split('.')[0])
                if linhas_total > 1000:
                    self.terminal.delete("1.0", f"{int(linhas_total - 1000)}.0")
                self.terminal.see("end")
            
            self.progress_bar.set(self.ui_progresso)
            self.lbl_stats.configure(text=self.ui_stats_text)
            self.lbl_status.configure(text=self.ui_status_text)
            
            self.after(100, self.atualizar_interface_periodico)

    def select_origin_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.root_dir = Path(path)
            self.lbl_origin.configure(text=str(self.root_dir), text_color="white")

    def alternar_pausa(self):
        self.pausado = not self.pausado
        self.btn_pause.configure(text="RETOMAR" if self.pausado else "PAUSAR")
        if self.pausado:
            self.log("Processo pausado pelo usuário.")
        else:
            self.log("Processo retomado.")

    def stop(self):
        self.stop_requested = True
        self.log("Solicitando parada imediata...")

    def bloquear_fechamento(self):
        """Callback acionado se o usuário tentar fechar a janela principal do Windows."""
        messagebox.showerror(
            "OPERAÇÃO BLOQUEADA", 
            "A cópia de produtos está em andamento! O programa não pode ser fechado até que o processo seja concluído ou parado definitivamente para evitar arquivos corrompidos."
        )

    def alternar_botoes_externos(self, state):
        """Desabilita recursivamente todos os botões e entradas de texto fora deste frame."""
        root = self.winfo_toplevel()
        self._set_state_recursive(root, state)

    def _set_state_recursive(self, widget, state):
        for child in widget.winfo_children():
            if child == self or self.is_ancestor_of(child):
                continue
            if isinstance(child, (ctk.CTkButton, ctk.CTkEntry)):
                try:
                    child.configure(state=state)
                except:
                    pass
            self._set_state_recursive(child, state)

    def is_ancestor_of(self, widget):
        parent = widget.master
        while parent:
            if parent == self:
                return True
            parent = parent.master
        return False

    def iniciar(self):
        if not self.root_dir or not self.root_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta raiz válida.")
            return

        # Define automaticamente a pasta de destino 00_PRODUTOS na raiz informada
        self.dest_dir = self.root_dir / "00_PRODUTOS"
        try:
            self.dest_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível criar a pasta de destino automática:\n{e}")
            return

        self.is_running = True
        self.pausado = False
        self.stop_requested = False
        
        # ATIVA TRAVAS DE SEGURANÇA DE INTERFACE (NO-ESCAPE)
        self.root_window = self.winfo_toplevel()
        self.original_close_handler = self.root_window.protocol("WM_DELETE_WINDOW")
        self.root_window.protocol("WM_DELETE_WINDOW", self.bloquear_fechamento)  # Intercepta Alt+F4 / Fechar
        self.alternar_botoes_externos("disabled")  # Desabilita botões externos (Voltar, Sidebar)

        # Bloqueia controles internos
        self.btn_start.configure(state="disabled")
        self.btn_origin.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="PAUSAR")
        self.btn_stop.configure(state="normal")

        self.terminal.delete("1.0", "end")
        self.log_queue = []
        self.atualizar_interface_periodico()

        threading.Thread(target=self.worker, daemon=True).start()

    def copiar_arquivo_com_abort(self, src, dst):
        """Copia um arquivo em blocos de 1MB permitindo pausa e parada instantânea."""
        buffer_size = 1024 * 1024  # 1MB
        with open(src, 'rb') as f_src, open(dst, 'wb') as f_dst:
            while True:
                if self.stop_requested:
                    raise InterruptedError("Operação interrompida pelo usuário.")
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)
                
                chunk = f_src.read(buffer_size)
                if not chunk:
                    break
                f_dst.write(chunk)

    def worker(self):
        try:
            self.log("Iniciando varredura profunda de subpastas...")
            self.start_time = time.time()
            
            # Dicionário para agrupar arquivos de vídeo por sua pasta pai (Pack)
            packs_mapeados = {}
            
            # os.walk para varrer recursivamente
            for root, dirs, files in os.walk(str(self.root_dir)):
                if self.stop_requested: 
                    break
                
                # Ignora a própria pasta de destino 00_PRODUTOS e pastas ocultas
                if "00_PRODUTOS" in root or f"{os.sep}." in root:
                    continue
                    
                parent_path = Path(root)
                
                for file in files:
                    if not file.startswith(".") and not file.startswith("._"):
                        ext = os.path.splitext(file)[1].lower()
                        if ext in self.allowed_video_ext:
                            if parent_path not in packs_mapeados:
                                packs_mapeados[parent_path] = []
                            packs_mapeados[parent_path].append(parent_path / file)

            if self.stop_requested:
                self.log("Operação cancelada durante a varredura.")
                return

            total_packs = len(packs_mapeados)
            self.log(f"Varredura concluída! Encontradas {total_packs} pastas de packs contendo vídeos.")

            if total_packs == 0:
                self.log("Nenhum vídeo qualificado encontrado nas subpastas.")
                return

            # Fase de planejamento: Seleciona os 20 vídeos aleatórios de cada pack e calcula a fila total
            fila_copia = []
            for pack_path, videos in packs_mapeados.items():
                qtd_disponivel = len(videos)
                qtd_selecionar = min(self.qty_to_copy, qtd_disponivel)
                videos_selecionados = random.sample(videos, qtd_selecionar)
                
                # Determina o Nicho (1º nível abaixo da raiz)
                try:
                    rel_path = pack_path.relative_to(self.root_dir)
                    nicho = rel_path.parts[0]  # O primeiro segmento é o nicho (ex: ANIMAIS)
                except Exception:
                    nicho = "OUTROS"

                # Define a pasta de destino do pack preservando o nome original do pack
                pack_name = pack_path.name
                dest_pack_dir = self.dest_dir / nicho / pack_name
                
                for v_path in videos_selecionados:
                    fila_copia.append((v_path, dest_pack_dir / v_path.name))

            total_arquivos_fila = len(fila_copia)
            self.log(f"Fila de cópia estruturada: {total_arquivos_fila} vídeos serão copiados.")

            copiados = 0
            erros = 0

            for idx, (src_file, dst_file) in enumerate(fila_copia, 1):
                if self.stop_requested:
                    break
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)

                # Garante que a subpasta de destino do nicho/pack existe
                dst_file.parent.mkdir(parents=True, exist_ok=True)

                self.log(f"  -> Copiando ({idx}/{total_arquivos_fila}): {src_file.name}")
                self.ui_status_text = f"Copiando: {src_file.name}"

                try:
                    # Executa a cópia em blocos com suporte a abort imediato
                    self.copiar_arquivo_com_abort(src_file, dst_file)
                    copiados += 1
                except InterruptedError as ie:
                    self.log(f"Processo interrompido: {ie}")
                    # Remove arquivo incompleto se foi cancelado no meio
                    if dst_file.exists():
                        try: 
                            os.remove(dst_file)
                        except: 
                            pass
                    break
                except Exception as e:
                    erros += 1
                    self.log(f"ERRO ao copiar {src_file.name}: {e}")
                    if dst_file.exists():
                        try: 
                            os.remove(dst_file)
                        except: 
                            pass

                # Atualiza métricas e progresso suave
                self.ui_progresso = idx / total_arquivos_fila
                elapsed = time.time() - self.start_time
                tempo_decorrido = time.strftime("%M:%S", time.gmtime(elapsed))
                velocidade = idx / elapsed if elapsed > 0 else 0
                restante = (total_arquivos_fila - idx) / velocidade if velocidade > 0 else 0
                tempo_restante = time.strftime("%M:%S", time.gmtime(restante))
                
                self.ui_stats_text = f"Copiados: {copiados}/{total_arquivos_fila} | Erros: {erros} | Tempo: {tempo_decorrido} | Restante: ~{tempo_restante}"

            # --- NOVA FUNCIONALIDADE: GERAÇÃO DE ÍNDICES TXT POR NICHO ---
            if copiados > 0 and not self.stop_requested:
                self.log("\nGerando arquivos de índice TXT para cada nicho...")
                for nicho_dir in self.dest_dir.iterdir():
                    if nicho_dir.is_dir():
                        nicho_name = nicho_dir.name
                        # Lista apenas as subpastas (packs), ignorando arquivos de texto existentes
                        packs_no_nicho = [p.name for p in nicho_dir.iterdir() if p.is_dir()]
                        if packs_no_nicho:
                            txt_path = nicho_dir / f"{nicho_name}.txt"
                            try:
                                with open(txt_path, "w", encoding="utf-8") as f_txt:
                                    f_txt.write(f"--- PACKS NO NICHO: {nicho_name} ---\n")
                                    for p_name in sorted(packs_no_nicho):
                                        f_txt.write(f"{p_name}\n")
                                self.log(f"  -> Criado índice: {txt_path.name} ({len(packs_no_nicho)} packs listados)")
                            except Exception as e:
                                self.log(f"Erro ao criar índice {nicho_name}.txt: {e}")

            # Resumo Final
            duracao = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
            self.log("\n" + "="*40)
            self.log("RESUMO FINAL DA OPERAÇÃO")
            self.log(f"Duração Total: {duracao}")
            self.log(f"Vídeos Copiados com Sucesso: {copiados}")
            self.log(f"Falhas/Erros: {erros}")
            self.log(f"Produtos salvos em: {self.dest_dir.name}/")
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
        
        # DESATIVA TODAS AS TRAVAS DE SEGURANÇA E RESTAURA COMPORTAMENTO PADRÃO
        if self.root_window:
            if self.original_close_handler:
                self.root_window.protocol("WM_DELETE_WINDOW", self.original_close_handler)
            else:
                self.root_window.protocol("WM_DELETE_WINDOW", self.root_window.destroy)
        self.alternar_botoes_externos("normal")  # Libera botões externos

        # Libera controles de navegação e inputs internos
        self.btn_start.configure(state="normal")
        self.btn_origin.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        
        messagebox.showinfo("Fim", "Processo de cópia de produtos finalizado.")