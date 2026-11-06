"""
FERRAMENTA: CRIADOR DE PACKS INTEGRADO (FACILITADORES) - VERSÃO ULTRA PERFORMANCE 6.0
LÓGICA UNIFICADA:
1. GERAÇÃO TEMPORAL: Cria uma pasta única para os packs da execução atual: RAIZ/GERACAO_[DATA_HORA].
2. VARREDURA ULTRA RÁPIDA: Usa os.scandir() para listar 23k+ arquivos instantaneamente.
3. EMBARALHAMENTO ALEATÓRIO: Aplica random.shuffle() na memória para coletar vídeos de forma 100% aleatória e instantânea.
4. NOMENCLATURA DINÂMICA (LÓGICA DO RENOMEADOR):
   - O nome do pack segue o padrão definido na UI (ex: Curiosity Facts Video Pack #{NUMERO} - {QTD_VIDEOS} Clips).
   - {NUMERO} é substituído por um número aleatório de 5 dígitos.
   - {QTD_VIDEOS} é a contagem exata de vídeos movidos para aquele pack.
5. ESTRUTURA DE PASTAS ATUALIZADA:
   - Os vídeos vão diretamente para a raiz do pack: GERACAO_[DATA_HORA]/[NOME_DO_PACK]/video.mp4 (sem pasta VIDEOS).
   - Apenas o arquivo LOG.TXT (completamente vazio) é criado na raiz do pack (README.TXT foi removido).
   - A extração de frames foi completamente removida para focar exclusivamente na separação ultra rápida de vídeos.
6. RELATÓRIO GERAL INTERNO: Cria o arquivo PACKS_NAME.TXT dentro da pasta GERACAO_[DATA_HORA] com todos os nomes de packs gerados.
7. INTERFACE THREAD-SAFE: Atualização suave de progresso e travamento de navegação durante a execução.
"""

import os
import random
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk


class CriadorPacksFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.allowed_video_ext = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mpeg", ".mpg"]
        self.is_running = False
        self.pausado = False
        self.stop_requested = False
        self.root_dir = None
        
        # Variáveis de controle de UI (Thread-Safe)
        self.ui_progresso = 0.0
        self.ui_stats_text = "Packs Criados: 0 | Vídeos Movidos: 0"
        self.ui_status_text = "Status: Aguardando Comando"
        self.log_queue = []
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Título
        ctk.CTkLabel(self, text="CRIADOR DE PACKS DE VÍDEOS INTEGRADO", 
                     font=("Segoe UI", 20, "bold")).pack(pady=(10, 15))

        # Painel de Configurações
        config_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        config_frame.pack(fill="x", padx=20, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        # 1. Seleção de Pasta Raiz
        ctk.CTkLabel(config_frame, text="Pasta Raiz:", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        folder_subframe = ctk.CTkFrame(config_frame, fg_color="transparent")
        folder_subframe.grid(row=0, column=1, padx=15, pady=10, sticky="ew")
        
        self.btn_folder = ctk.CTkButton(folder_subframe, text="📁 SELECIONAR PASTA", 
                                        command=self.select_folder, fg_color="#3d3d3d", width=150)
        self.btn_folder.pack(side="left")
        self.lbl_folder = ctk.CTkLabel(folder_subframe, text="Nenhum diretório selecionado", text_color="gray")
        self.lbl_folder.pack(side="left", padx=10)

        # 2. Padrão de Nome do Pack
        ctk.CTkLabel(config_frame, text="Padrão de Nome:", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, padx=15, pady=10, sticky="w")
        self.entry_pattern = ctk.CTkEntry(config_frame, placeholder_text="Ex: Curiosity Facts Video Pack #{NUMERO} - {QTD_VIDEOS} Clips", 
                                             height=35, fg_color="#0f0f0f")
        self.entry_pattern.grid(row=1, column=1, padx=15, pady=10, sticky="ew")
        self.entry_pattern.insert(0, "Curiosity Facts Video Pack #{NUMERO} - {QTD_VIDEOS} Clips")

        # 3. Quantidade de Vídeos por Pack (Obrigatório)
        ctk.CTkLabel(config_frame, text="Vídeos por Pack:", font=("Segoe UI", 12, "bold")).grid(row=2, column=0, padx=15, pady=10, sticky="w")
        self.entry_videos_qty = ctk.CTkEntry(config_frame, placeholder_text="Ex: 50 (Obrigatório)", 
                                             height=35, fg_color="#0f0f0f")
        self.entry_videos_qty.grid(row=2, column=1, padx=15, pady=10, sticky="ew")

        # 4. Quantidade de Packs (Opcional)
        ctk.CTkLabel(config_frame, text="Qtd. de Packs:", font=("Segoe UI", 12, "bold")).grid(row=3, column=0, padx=15, pady=10, sticky="w")
        self.entry_packs_qty = ctk.CTkEntry(config_frame, placeholder_text="Deixe vazio para criar o máximo possível (Opcional)", 
                                            height=35, fg_color="#0f0f0f")
        self.entry_packs_qty.grid(row=3, column=1, padx=15, pady=10, sticky="ew")

        # Terminal de Logs
        self.terminal = ctk.CTkTextbox(self, height=220, font=("Courier New", 12), 
                                       fg_color="#000000", text_color="#3498db")
        self.terminal.pack(fill="both", expand=True, padx=20, pady=10)

        # Barra de Status e Progresso
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20)
        
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=800, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=5)

        self.lbl_stats = ctk.CTkLabel(self.status_frame, text="Packs Criados: 0 | Vídeos Movidos: 0", 
                                      font=("Segoe UI", 11, "bold"))
        self.lbl_stats.pack(pady=2)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Aguardando Comando", font=("Segoe UI", 12))
        self.lbl_status.pack(pady=(0, 10))

        # Controles
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.ctrl_frame, text="▶ INICIAR ORGANIZAÇÃO", fg_color="#2ecc71", 
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

    def stop(self):
        self.stop_requested = True
        self.log("Solicitando parada segura...")

    def iniciar(self):
        if not self.root_dir or not self.root_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta raiz válida.")
            return

        self.pattern = self.entry_pattern.get().strip()
        if not self.pattern:
            messagebox.showwarning("Aviso", "O padrão de nome do pack não pode estar vazio.")
            return

        # Validação obrigatória de vídeos por pack
        try:
            self.v_per_pack = int(self.entry_videos_qty.get().strip())
            if self.v_per_pack <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Aviso", "A quantidade de vídeos por pack deve ser um número inteiro maior que zero.")
            return

        # Validação opcional de quantidade de packs
        packs_input = self.entry_packs_qty.get().strip()
        if packs_input:
            try:
                self.packs_limit = int(packs_input)
                if self.packs_limit <= 0: raise ValueError
            except ValueError:
                messagebox.showwarning("Aviso", "A quantidade de packs deve ser um número inteiro maior que zero (or deixe vazio).")
                return
        else:
            self.packs_limit = None

        self.is_running = True
        self.pausado = False
        self.stop_requested = False

        # Bloqueia controles de navegação e inputs
        self.btn_start.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
        self.entry_pattern.configure(state="disabled")
        self.entry_videos_qty.configure(state="disabled")
        self.entry_packs_qty.configure(state="disabled")
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
            self.log("Iniciando varredura ultra rápida de vídeos qualificados...")
            # OTIMIZAÇÃO CRÍTICA: os.scandir() evita milhares de chamadas stat() individuais
            videos_disponiveis = []
            root_path_str = str(self.root_dir)
            with os.scandir(root_path_str) as entries:
                for entry in entries:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            name = entry.name
                            if not name.startswith(".") and not name.startswith("._"):
                                ext = os.path.splitext(name)[1].lower()
                                if ext in self.allowed_video_ext:
                                    videos_disponiveis.append(Path(entry.path))
                    except Exception:
                        continue

            total_videos = len(videos_disponiveis)
            self.log(f"Varredura concluída! Encontrados {total_videos} vídeos qualificados na raiz.")

            if total_videos < self.v_per_pack:
                self.log(f"Quantidade de vídeos insuficientes para criar sequer 1 pack de {self.v_per_pack} vídeos.")
                return

            # EMBARALHAMENTO ALEATÓRIO E INSTANTÂNEO:
            # Mistura a lista completa na memória antes de fatiar os lotes.
            self.log("Embaralhando a lista de vídeos de forma aleatória...")
            random.shuffle(videos_disponiveis)

            # Determina quantos packs serão criados
            max_packs_possiveis = total_videos // self.v_per_pack
            packs_a_criar = max_packs_possiveis
            if self.packs_limit is not None:
                packs_a_criar = min(self.packs_limit, max_packs_possiveis)

            self.log(f"Planejado criar: {packs_a_criar} pack(s) de {self.v_per_pack} vídeos cada.")

            # Cria a pasta da Geração atual na raiz
            timestamp_geracao = datetime.now().strftime("%Y%m%d_%H%M%S")
            geracao_dir_name = f"GERACAO_{timestamp_geracao}"
            geracao_dir = self.root_dir / geracao_dir_name
            geracao_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"Pasta da geração criada: {geracao_dir.name}")

            packs_criados = 0
            videos_movidos = 0
            nomes_gerados = []

            for p in range(1, packs_a_criar + 1):
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)
                if self.stop_requested: 
                    break

                # Seleciona os vídeos para este lote (já aleatórios devido ao shuffle prévio)
                lote_videos = videos_disponiveis[(p-1)*self.v_per_pack : p*self.v_per_pack]
                qtd_videos_lote = len(lote_videos)

                # Gera o número randômico de 5 dígitos para o pack
                random_num = f"{random.randint(10000, 99999)}"

                # Formata o nome do pack usando a lógica do renomeador
                pack_name = self.pattern.replace("{NUMERO}", random_num).replace("{QTD_VIDEOS}", str(qtd_videos_lote))
                
                # OTIMIZAÇÃO CRÍTICA: chr(92) representa a barra invertida (\) de forma segura sem quebrar a sintaxe
                for char in [chr(92), '/', ':', '*', '?', '"', '<', '>', '|']:
                    pack_name = pack_name.replace(char, "_")

                # Cria a pasta do pack dentro da geração atual
                pack_dir = geracao_dir / pack_name
                pack_dir.mkdir(parents=True, exist_ok=True)
                self.log(f"\nCriando {pack_name}...")

                for idx, video_path in enumerate(lote_videos, 1):
                    while self.pausado and not self.stop_requested:
                        time.sleep(0.1)
                    if self.stop_requested: 
                        break

                    # Move o vídeo DIRETAMENTE para a raiz da pasta do pack (os.rename é instantâneo)
                    dest_video = pack_dir / video_path.name
                    try:
                        os.rename(str(video_path), str(dest_video))
                    except Exception as e:
                        self.log(f"Erro ao mover {video_path.name}: {e}")
                        continue

                    videos_movidos += 1
                    self.ui_status_text = f"Movendo vídeo {idx}/{qtd_videos_lote} para {pack_name}..."

                    # Atualiza progresso e estatísticas
                    self.ui_progresso = (videos_movidos) / (packs_a_criar * self.v_per_pack)
                    self.ui_stats_text = f"Packs: {packs_criados+1}/{packs_a_criar} | Vídeos: {videos_movidos}"

                # Cria apenas o LOG.TXT vazio dentro do pack (README.TXT não existirá mais)
                self.criar_documentacao(pack_dir)
                nomes_gerados.append(pack_name)
                packs_criados += 1
                self.log(f"Sucesso: {pack_name} concluído com {qtd_videos_lote} vídeos.")

            # Salva a lista de nomes gerados no arquivo PACKS_NAME.TXT dentro da pasta de GERAÇÃO
            if nomes_gerados:
                self.salvar_lista_nomes(nomes_gerados, geracao_dir)

            # Resumo Final no Terminal
            self.log("\n" + "="*40)
            self.log("RESUMO FINAL DA OPERAÇÃO")
            self.log(f"Packs Criados com Sucesso: {packs_criados}")
            self.log(f"Total de Vídeos Organizados: {videos_movidos}")
            self.log(f"Vídeos Restantes na Raiz: {total_videos - videos_movidos}")
            self.log(f"Lista de nomes salva em: {geracao_dir.name}/PACKS_NAME.TXT")
            self.log("="*40)

        except Exception as e:
            self.log(f"ERRO CRÍTICO NO PROCESSO: {e}")
        finally:
            self.finalizar()

    def criar_documentacao(self, pack_dir):
        """Gera apenas o arquivo LOG.TXT completamente vazio dentro do pack."""
        try:
            # LOG.TXT completamente vazio
            with open(pack_dir / "LOG.TXT", "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            self.log(f"Erro ao criar LOG.TXT: {e}")

    def salvar_lista_nomes(self, lista_nomes, geracao_dir):
        """Escreve a lista de nomes gerados no arquivo PACKS_NAME.TXT dentro da pasta de geração."""
        caminho_txt = geracao_dir / "PACKS_NAME.TXT"
        try:
            with open(caminho_txt, "w", encoding="utf-8") as f:
                for nome in lista_nomes:
                    f.write(f"{nome}\n")
            self.log("Arquivo PACKS_NAME.TXT gerado com sucesso dentro da pasta de geração.")
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
        self.entry_videos_qty.configure(state="normal")
        self.entry_packs_qty.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="normal")
            
        messagebox.showinfo("Fim", "Processo de criação de packs finalizado.")