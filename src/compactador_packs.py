"""
FERRAMENTA: COMPACTADOR CRIPTOGRAFADO DE PACKS - VERSÃO TURBO 7-ZIP (FACILITADORES) - VERSÃO 3.8
LÓGICA DE VELOCIDADE EXTREMA E FEEDBACK AO VIVO:
1. MOTOR NATIVO C++ COM VERBOSIDADE (-bb1 -bsp1): Utiliza o 7-Zip com progresso detalhado e forçado ao vivo.
2. PARADA IMEDIATA (ACTIVE KILL): O botão PARAR mata o processo do 7-Zip diretamente no Kernel do Windows.
3. LEITURA CARACTERE POR CARACTERE (REAL-TIME): Captura a saída do 7-Zip dividindo por \n e \r, evitando travamentos de buffer.
4. PROGRESSO ULTRA SUAVE: Atualiza a barra de progresso e a porcentagem de forma contínua com base no feedback real do 7-Zip.
5. SEGURANÇA MÁXIMA: Aplica senha alfanumérica de 30 caracteres com criptografia AES-256 real (inviolável).
6. SELEÇÃO DE DESTINO: Permite selecionar manualmente onde os arquivos compactados e o relatório de senhas serão salvos.
7. PADRÃO DE NOME DO ARQUIVO DE SENHAS: O arquivo TXT gerado se chama "SENHA - [NOME_DA_PASTA_RAIZ].txt" e seu conteúdo
   segue o padrão original "NOME_DO_ARQUIVO = [SENHA]".
8. TRAVAS DE SEGURANÇA MÁXIMA (NO-ESCAPE):
   - Bloqueia o fechamento da janela (Alt+F4 / Botão X) enquanto o processo estiver rodando.
   - Desabilita recursivamente todos os botões e menus de navegação externos ao frame.
"""

import os
import re
import secrets
import shutil
import string
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk


class CompactadorPacksFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.is_running = False
        self.pausado = False
        self.stop_requested = False
        self.start_time = 0
        self.root_dir = None
        self.dest_dir = None
        self.root_window = None
        self.original_close_handler = None
        self.caminho_7z = None
        self.current_process = None  # Guarda o processo ativo para encerramento imediato
        
        # Variáveis de controle de UI (Thread-Safe)
        self.ui_progresso = 0.0
        self.ui_stats_text = "Packs Compactados: 0/0 | Tempo: 00:00 | Restante: ~00:00"
        self.ui_status_text = "Status: Aguardando Comando"
        self.log_queue = []
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Título
        ctk.CTkLabel(self, text="COMPACTADOR CRIPTOGRAFADO DE PACKS (7-ZIP TURBO)", 
                     font=("Segoe UI", 20, "bold")).pack(pady=(10, 15))

        # Painel de Configurações
        config_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        config_frame.pack(fill="x", padx=20, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        # 1. Seleção de Pasta Raiz (Origem)
        ctk.CTkLabel(config_frame, text="Pasta Raiz:", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        folder_origin_subframe = ctk.CTkFrame(config_frame, fg_color="transparent")
        folder_origin_subframe.grid(row=0, column=1, padx=15, pady=10, sticky="ew")
        
        self.btn_origin = ctk.CTkButton(folder_origin_subframe, text="📁 SELECIONAR PASTA", 
                                        command=self.select_origin_folder, fg_color="#3d3d3d", width=160)
        self.btn_origin.pack(side="left")
        self.lbl_origin = ctk.CTkLabel(folder_origin_subframe, text="Selecione a pasta raiz contendo os packs", text_color="gray")
        self.lbl_origin.pack(side="left", padx=10)

        # 2. Seleção de Pasta de Destino (Salvar ZIPs)
        ctk.CTkLabel(config_frame, text="Pasta Destino:", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, padx=15, pady=10, sticky="w")
        folder_dest_subframe = ctk.CTkFrame(config_frame, fg_color="transparent")
        folder_dest_subframe.grid(row=1, column=1, padx=15, pady=10, sticky="ew")
        
        self.btn_dest = ctk.CTkButton(folder_dest_subframe, text="💾 SELECIONAR DESTINO", 
                                      command=self.select_dest_folder, fg_color="#3d3d3d", width=160)
        self.btn_dest.pack(side="left")
        self.lbl_dest = ctk.CTkLabel(folder_dest_subframe, text="Selecione onde os arquivos compactados serão salvos", text_color="gray")
        self.lbl_dest.pack(side="left", padx=10)

        # Terminal de Logs
        self.terminal = ctk.CTkTextbox(self, height=250, font=("Courier New", 12), 
                                       fg_color="#000000", text_color="#9b59b6")
        self.terminal.pack(fill="both", expand=True, padx=20, pady=10)

        # Barra de Status e Progresso
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20)
        
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=800, progress_color="#9b59b6")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=5)

        self.lbl_stats = ctk.CTkLabel(self.status_frame, text="Packs Compactados: 0/0 | Tempo: 00:00 | Restante: ~00:00", 
                                      font=("Segoe UI", 11, "bold"))
        self.lbl_stats.pack(pady=2)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Aguardando Comando", font=("Segoe UI", 12))
        self.lbl_status.pack(pady=(0, 10))

        # Controles
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.ctrl_frame, text="🔒 INICIAR COMPACTAÇÃO", fg_color="#9b59b6", 
                                       hover_color="#8e44ad", width=220, height=45, 
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

    def select_dest_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_dir = Path(path)
            self.lbl_dest.configure(text=str(self.dest_dir), text_color="white")

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
        
        # INTERRUPÇÃO ATIVA: Mata o processo do 7-Zip diretamente no Windows
        if self.current_process:
            try:
                self.log("Forçando encerramento do processo do 7-Zip...")
                self.current_process.kill()  # Finaliza o processo C++ instantaneamente
            except Exception as e:
                self.log(f"Erro ao forçar parada do processo: {e}")

    def bloquear_fechamento(self):
        """Callback acionado se o usuário tentar fechar a janela principal do Windows."""
        messagebox.showerror(
            "OPERAÇÃO BLOQUEADA", 
            "A compactação criptografada está em andamento! O programa não pode ser fechado até que o processo seja concluído ou parado definitivamente para evitar arquivos corrompidos."
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

    def localizar_7z(self):
        """Varre caminhos comuns do sistema para encontrar o executável do 7-Zip."""
        caminhos = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "7-Zip" / "7z.exe",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "7-Zip" / "7z.exe",
            Path(r"C:\Program Files\7-Zip\7z.exe"),
            Path(r"C:\Program Files (x86)\7-Zip\7z.exe")
        ]
        for c in caminhos:
            try:
                if c.exists():
                    return c
            except:
                pass
        
        # Tenta verificar se está mapeado no PATH global do sistema
        sh_path = shutil.which("7z")
        if sh_path:
            return Path(sh_path)
            
        return None

    def iniciar(self):
        self.caminho_7z = self.localizar_7z()
        if not self.caminho_7z:
            messagebox.showerror(
                "7-Zip Não Encontrado", 
                r"O executável '7z.exe' não foi localizado no seu sistema. Por favor, instale o 7-Zip no caminho padrão (C:\Program Files\7-Zip) para utilizar a compactação turbo com senha."
            )
            return

        if not self.root_dir or not self.root_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta raiz válida.")
            return

        if not self.dest_dir or not self.dest_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta de destino válida.")
            return

        self.is_running = True
        self.pausado = False
        self.stop_requested = False
        self.current_process = None
        
        # ATIVA TRAVAS DE SEGURANÇA DE INTERFACE (NO-ESCAPE)
        self.root_window = self.winfo_toplevel()
        self.original_close_handler = self.root_window.protocol("WM_DELETE_WINDOW")
        self.root_window.protocol("WM_DELETE_WINDOW", self.bloquear_fechamento)  # Intercepta Alt+F4 / Fechar
        self.alternar_botoes_externos("disabled")  # Desabilita botões externos (Voltar, Sidebar)

        # Bloqueia controles internos
        self.btn_start.configure(state="disabled")
        self.btn_origin.configure(state="disabled")
        self.btn_dest.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="PAUSAR")
        self.btn_stop.configure(state="normal")

        self.terminal.delete("1.0", "end")
        self.log_queue = []
        self.atualizar_interface_periodico()

        threading.Thread(target=self.worker, daemon=True).start()

    def format_pack_name(self, name):
        """Formata o nome da pasta de acordo com o padrão solicitado (Uppercase, espaços/hifens por sublinhados)."""
        cleaned = name.upper()
        cleaned = re.sub(r'[\s\-]+', '_', cleaned)  # substitui espaços e hifens por sublinhado
        cleaned = re.sub(r'_+', '_', cleaned)        # colapsa múltiplos sublinhados
        return cleaned.strip('_')

    def gerar_senha_ultra_segura(self):
        """Gera uma senha alfanumérica de 30 caracteres com letras maiúsculas, minúsculas, números e símbolos."""
        caracteres = string.ascii_letters + string.digits + "!@#$%&*()_+-=[]{}|;:,.<>?"
        return "".join(secrets.choice(caracteres) for _ in range(30))

    def worker(self):
        try:
            self.log("Mapeando subpastas de packs na origem...")
            self.start_time = time.time()
            
            subpastas = []
            with os.scandir(str(self.root_dir)) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        # Ignora pastas de sistema, a pasta de destino automática e pastas que comecem com 00
                        if not entry.name.startswith(".") and not entry.name.startswith("00") and not entry.name.startswith("COMPACTADOS_"):
                            subpastas.append(Path(entry.path))

            total_packs = len(subpastas)
            self.log(f"Encontradas {total_packs} pastas de packs qualificadas para compactação.")

            if total_packs == 0:
                self.log("Nenhuma pasta de pack encontrada para processar.")
                return

            processados = 0
            erros = 0
            mapeamento_senhas = []

            for idx, pasta_pack in enumerate(subpastas, 1):
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)
                if self.stop_requested: 
                    break

                # Formata o nome de saída
                nome_formatado = self.format_pack_name(pasta_pack.name)
                self.log(f"\n[{idx}/{total_packs}] Processando: {pasta_pack.name}")
                
                # Mapeia todos os arquivos internos para calcular o progresso real
                arquivos_no_pack = []
                for root, dirs, files in os.walk(str(pasta_pack)):
                    for file in files:
                        if not file.startswith(".") and not file.startswith("._"):
                            arquivos_no_pack.append(Path(root) / file)
                
                total_arquivos_pack = len(arquivos_no_pack)
                self.log(f"Mapeado {total_arquivos_pack} arquivos internos para empacotamento.")

                # Caminho final do arquivo ZIP criptografado
                final_zip_path = self.dest_dir / f"{nome_formatado}.zip"

                try:
                    # 1. Gera a senha ultra segura de 30 caracteres
                    senha = self.gerar_senha_ultra_segura()

                    # 2. Executa o 7-Zip via Subprocesso em tempo real (Modo Turbo AES-256)
                    self.log("Iniciando compactação turbo com criptografia AES-256...")
                    
                    # Comando do 7-Zip para criar ZIP com criptografia AES-256, compressão ultra rápida (mx1)
                    # Adicionado o parâmetro -bb1 para listar cada arquivo processado ao vivo
                    # Adicionado o parâmetro -bsp1 para forçar o envio de progresso percentual ao vivo
                    comando = [
                        str(self.caminho_7z), "a", "-tzip", 
                        f"-p{senha}", "-mem=AES256", "-mx=1", "-bb1", "-bsp1",
                        str(final_zip_path), "*"
                    ]

                    # Executa ocultando a janela preta do CMD no Windows, com codificação segura
                    self.current_process = subprocess.Popen(
                        comando,
                        cwd=str(pasta_pack),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1,
                        creationflags=0x08000000  # CREATE_NO_WINDOW
                    )

                    files_processed = 0
                    buffer_str = ""
                    
                    # OTIMIZAÇÃO CRÍTICA: Lê caractere por caractere para capturar o Carriage Return (\r) do 7-Zip
                    while True:
                        char = self.current_process.stdout.read(1)
                        if not char:
                            break
                        
                        if self.stop_requested:
                            break
                        while self.pausado and not self.stop_requested:
                            time.sleep(0.1)

                        # Se encontrar quebra de linha (\n) ou retorno de carro (\r), processa a linha acumulada
                        if char in ('\n', '\r'):
                            line_clean = buffer_str.strip()
                            if line_clean:
                                # 1. Detecta arquivos sendo adicionados
                                if "Compressing" in line_clean:
                                    files_processed += 1
                                    file_name = line_clean.replace("Compressing", "").strip()
                                    file_name = re.sub(r'^[\s\:\-\+]+', '', file_name)
                                    self.log(f"  -> Compactando ({files_processed}/{total_arquivos_pack}): {file_name}")
                                
                                # 2. Detecta progresso percentual do 7-Zip (ex: " 45% 123" ou "100%")
                                pct_match = re.search(r'(\d+)%', line_clean)
                                if pct_match:
                                    pct = int(pct_match.group(1))
                                    # Atualização suave de progresso na barra
                                    percent_files = pct / 100.0
                                    self.ui_progresso = (idx - 1 + percent_files) / total_packs
                                    self.ui_status_text = f"Pack {idx}/{total_packs} | Compactando: {pct}% | {files_processed}/{total_arquivos_pack} arquivos"
                            
                            buffer_str = ""
                        else:
                            buffer_str += char

                    self.current_process.wait()

                    # Se foi parado, remove o arquivo incompleto gerado para evitar lixo
                    if self.stop_requested: 
                        if final_zip_path.exists():
                            try: os.remove(final_zip_path)
                            except: pass
                        break

                    if self.current_process.returncode == 0:
                        # Armazena a senha gerada para o relatório final
                        mapeamento_senhas.append((final_zip_path.name, senha))
                        processados += 1
                        self.log(f"Sucesso: {final_zip_path.name} gerado e protegido com AES-256.")
                    else:
                        raise RuntimeError(f"O 7-Zip retornou código de erro: {self.current_process.returncode}")

                except Exception as e:
                    erros += 1
                    self.log(f"ERRO ao processar {pasta_pack.name}: {e}")
                    if final_zip_path.exists():
                        try: os.remove(final_zip_path)
                        except: pass

                # Atualiza métricas e progresso final do lote
                self.ui_progresso = idx / total_packs
                elapsed = time.time() - self.start_time
                tempo_decorrido = time.strftime("%M:%S", time.gmtime(elapsed))
                velocidade = idx / elapsed if elapsed > 0 else 0
                restante = (total_packs - idx) / velocidade if velocidade > 0 else 0
                tempo_restante = time.strftime("%M:%S", time.gmtime(restante))
                
                self.ui_stats_text = f"Packs: {idx}/{total_packs} | Erros: {erros} | Tempo: {tempo_decorrido} | Restante: ~{tempo_restante}"

            # 3. Cria o arquivo senhas.txt no diretório de destino automático
            if mapeamento_senhas and not self.stop_requested:
                self.salvar_arquivo_senhas(mapeamento_senhas)

            # Resumo Final
            duracao = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
            self.log("\n" + "="*40)
            self.log("RESUMO FINAL DA COMPACTAÇÃO")
            self.log(f"Duração Total: {duracao}")
            self.log(f"Packs Compactados com Sucesso: {processados}")
            self.log(f"Erros Encontrados: {erros}")
            if not self.stop_requested:
                self.log(f"Relatório de senhas salvo em: {self.dest_dir.name}/SENHA - {self.root_dir.name}.txt")
            self.log("="*40)

        except Exception as e:
            self.log(f"ERRO CRÍTICO NO PROCESSO: {e}")
        finally:
            self.finalizar()

    def salvar_arquivo_senhas(self, mapeamento_senhas):
        """Cria ou anexa as senhas geradas no arquivo senhas.txt no diretório de destino automático."""
        caminho_senhas = self.dest_dir / f"SENHA - {self.root_dir.name}.txt"
        try:
            # Abre em modo append para não apagar senhas de execuções anteriores na mesma pasta
            with open(caminho_senhas, "a", encoding="utf-8") as f:
                f.write(f"\n--- EXECUÇÃO EM {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ---\n")
                for nome_arquivo, senha in mapeamento_senhas:
                    # REVERTIDO PARA O PADRÃO ORIGINAL: NOME_DO_ARQUIVO = [SENHA]
                    f.write(f"{nome_arquivo} = {senha}\n")
            self.log(f"Relatório SENHA - {self.root_dir.name}.txt atualizado com sucesso no destino.")
        except Exception as e:
            self.log(f"Erro ao salvar arquivo de senhas: {e}")

    def finalizar(self):
        self.after(0, self.finalizar_main_thread)

    def finalizar_main_thread(self):
        self.is_running = False
        self.current_process = None
        
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
        self.btn_dest.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        
        messagebox.showinfo("Fim", "Processo de compactação criptografada finalizado.")
        