"""
FERRAMENTA: EXTRATOR DE ARQUIVOS EM MASSA (FACILITADORES) - VERSÃO ULTRA PERFORMANCE 5.7
LÓGICA RECURSIVA DINÂMICA E ORGANIZAÇÃO INDEPENDENTE:
1. MOTOR HÍBRIDO DE EXTRAÇÃO: Utiliza o 7-Zip do sistema (se instalado) para extrair qualquer formato com 100% de sucesso.
2. FALLBACK NATIVO: Caso o 7-Zip não esteja disponível, utiliza as bibliotecas nativas do Python (zipfile, tarfile, etc.).
3. VARREDURA DINÂMICA: Identifica recursivamente todos os formatos conhecidos (.zip, .rar, .7z, .tar, .gz, .tgz, .bz2, .tbz2, .xz, .txz, .zipx, .cab).
4. FILA DINÂMICA: Continua varrendo e extraindo até que não reste nenhum arquivo compactado pendente (processa arquivos aninhados).
5. EXTRAÇÃO LOCALIZADA: Extrai os arquivos diretamente na subpasta onde o arquivo compactado se encontra.
6. FUNÇÃO INDEPENDENTE DE MOVIMENTAÇÃO: Permite apenas mover todos os arquivos compactados das subpastas
   para a pasta central '00_COMPACTADOS' na raiz, sem realizar a extração.
7. LIMPEZA DE METADADOS: Varre a pasta extraída eliminando arquivos temporários do macOS ('._').
8. ORGANIZAÇÃO DE ORIGINAIS: Move os arquivos compactados originais para a pasta '00_COMPACTADOS' na raiz após o sucesso.
9. CONTROLES DE FLUXO: Permite Iniciar, Pausar/Retomar e Parar a extração ou movimentação em tempo real de forma segura.
10. INTERFACE THREAD-SAFE: Atualizações visuais e logs processados via polling a cada 100ms para evitar travamentos.
"""

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

# Importações dinâmicas para evitar travamento caso as bibliotecas não estejam instaladas
try:
    import zipfile
except ImportError:
    zipfile = None
try:
    import tarfile
except ImportError:
    tarfile = None
try:
    import rarfile
except ImportError:
    rarfile = None
try:
    import py7zr
except ImportError:
    py7zr = None

class ExtrairArquivosFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        # Lista completa e homologada de todos os formatos conhecidos de compactação
        self.compressed_extensions = [
            '.zip', '.rar', '.7z', '.tar', '.gz', '.tgz', 
            '.bz2', '.tbz2', '.xz', '.txz', '.zipx', '.cab'
        ]
        self.is_running = False
        self.pausado = False
        self.stop_requested = False
        self.start_time = 0
        self.root_dir = None
        
        # Variáveis de controle de UI (Thread-Safe)
        self.ui_progresso = 0.0
        self.ui_stats_text = "Arquivos Processados: 0/0 | Extraídos: 0 | Erros: 0"
        self.ui_status_text = "Status: Aguardando Comando"
        self.log_queue = []
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # Título
        ctk.CTkLabel(self, text="EXTRATOR DE ARQUIVOS EM MASSA (RECURSIVO)", 
                     font=("Segoe UI", 20, "bold")).pack(pady=(10, 15))

        # Painel de Configurações
        config_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        config_frame.pack(fill="x", padx=20, pady=10)
        config_frame.grid_columnconfigure(1, weight=1)

        # Seleção de Pasta Raiz
        ctk.CTkLabel(config_frame, text="Pasta de Trabalho:", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, padx=15, pady=15, sticky="w")
        folder_subframe = ctk.CTkFrame(config_frame, fg_color="transparent")
        folder_subframe.grid(row=0, column=1, padx=15, pady=15, sticky="ew")
        
        self.btn_folder = ctk.CTkButton(folder_subframe, text="📁 SELECIONAR PASTA", 
                                        command=self.select_folder, fg_color="#3d3d3d", width=150)
        self.btn_folder.pack(side="left")
        self.lbl_folder = ctk.CTkLabel(folder_subframe, text="Nenhum diretório selecionado", text_color="gray")
        self.lbl_folder.pack(side="left", padx=10)

        # Terminal de Logs (Estilo Console)
        self.terminal = ctk.CTkTextbox(self, height=280, font=("Courier New", 12), 
                                       fg_color="#000000", text_color="#3498db")
        self.terminal.pack(fill="both", expand=True, padx=20, pady=10)

        # Barra de Status e Progresso
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20)
        
        self.progress_bar = ctk.CTkProgressBar(self.status_frame, width=800, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=5)

        self.lbl_stats = ctk.CTkLabel(self.status_frame, text="Arquivos Processados: 0/0 | Extraídos: 0 | Erros: 0", 
                                      font=("Segoe UI", 11, "bold"))
        self.lbl_stats.pack(pady=2)

        self.lbl_status = ctk.CTkLabel(self, text="Status: Aguardando Comando", font=("Segoe UI", 12))
        self.lbl_status.pack(pady=(0, 10))

        # Controles
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.ctrl_frame, text="▶ INICIAR EXTRAÇÃO", fg_color="#2ecc71", 
                                       hover_color="#27ae60", width=180, height=45, 
                                       font=("Segoe UI", 13, "bold"), command=self.iniciar)
        self.btn_start.grid(row=0, column=0, padx=5)

        # Botão: Mover Compactados de forma independente
        self.btn_move_only = ctk.CTkButton(self.ctrl_frame, text="📦 MOVER COMPACTADOS", fg_color="#e67e22", 
                                           hover_color="#d35400", width=180, height=45, 
                                           font=("Segoe UI", 13, "bold"), command=self.iniciar_movimentacao)
        self.btn_move_only.grid(row=0, column=1, padx=5)

        self.btn_pause = ctk.CTkButton(self.ctrl_frame, text="PAUSAR", state="disabled", 
                                       width=110, height=45, command=self.alternar_pausa)
        self.btn_pause.grid(row=0, column=2, padx=5)

        self.btn_stop = ctk.CTkButton(self.ctrl_frame, text="PARAR", fg_color="#e74c3c", 
                                      width=110, height=45, state="disabled", command=self.stop)
        self.btn_stop.grid(row=0, column=3, padx=5)

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

    def bloquear_fechamento(self):
        """Callback acionado se o usuário tentar fechar a janela principal do Windows."""
        messagebox.showerror(
            "OPERAÇÃO BLOQUEADA", 
            "A operação está em andamento! O programa não pode ser fechado até que o processo seja concluído ou parado definitivamente para evitar arquivos corrompidos."
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
        if not self.root_dir or not self.root_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta de trabalho válida.")
            return
        
        self.is_running = True
        self.pausado = False
        self.stop_requested = False
        
        # Bloqueia controles de navegação e inputs
        self.btn_start.configure(state="disabled")
        self.btn_move_only.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="PAUSAR")
        self.btn_stop.configure(state="normal")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="disabled")
            
        self.terminal.delete("1.0", "end")
        self.log_queue = []
        self.atualizar_interface_periodico()
        
        threading.Thread(target=self.worker, daemon=True).start()

    def iniciar_movimentacao(self):
        if not self.root_dir or not self.root_dir.exists():
            messagebox.showwarning("Aviso", "Selecione uma pasta de trabalho válida.")
            return
        
        self.is_running = True
        self.pausado = False
        self.stop_requested = False
        
        # Bloqueia controles de navegação e inputs
        self.btn_start.configure(state="disabled")
        self.btn_move_only.configure(state="disabled")
        self.btn_folder.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="PAUSAR")
        self.btn_stop.configure(state="normal")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="disabled")
            
        self.terminal.delete("1.0", "end")
        self.log_queue = []
        self.atualizar_interface_periodico()
        
        threading.Thread(target=self.worker_mover, daemon=True).start()

    def worker(self):
        try:
            self.log("Iniciando varredura profunda e recursiva de arquivos compactados...")
            self.start_time = time.time()
            
            processed_files = set()
            extracted_total = 0
            errors_total = 0
            processed_count = 0
            
            # Pasta central para organizar os arquivos compactados antigos na raiz
            compactados_dir = self.root_dir / "00_COMPACTADOS"

            # Tenta localizar o 7-Zip para extração ultra rápida e compatibilidade total
            caminho_7z = self.localizar_7z()
            if caminho_7z:
                self.log(f"Motor 7-Zip Turbo localizado em: {caminho_7z}")
            else:
                self.log("7-Zip não localizado. Utilizando bibliotecas padrão do Python (Fallback).")

            while True:
                if self.stop_requested:
                    break
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)
                
                # Varredura dinâmica e recursiva (ignora a pasta 00_COMPACTADOS e pastas ocultas)
                all_compressed = []
                for root, dirs, files in os.walk(str(self.root_dir)):
                    if "00_COMPACTADOS" in root or f"{os.sep}." in root:
                        continue
                    for f in files:
                        if not f.startswith(".") and not f.startswith("._"):
                            ext = os.path.splitext(f)[1].lower()
                            if ext in self.compressed_extensions:
                                full_path = Path(root) / f
                                if full_path not in processed_files:
                                    all_compressed.append(full_path)
                
                # O total descoberto é a soma do que já processamos com o que ainda resta na fila
                total_discovered = processed_count + len(all_compressed)
                
                # Se não houver mais arquivos compactados pendentes, encerra o loop
                if not all_compressed:
                    break
                
                # Pega o primeiro arquivo da fila dinâmica
                file_path = all_compressed[0]
                processed_count += 1
                processed_files.add(file_path)
                
                # Mostra o caminho relativo para melhor visualização no log
                try:
                    rel_path = file_path.relative_to(self.root_dir)
                except ValueError:
                    rel_path = file_path.name
                self.log(f"\n[{processed_count}/{total_discovered}] Processando: {rel_path}")
                self.ui_status_text = f"Extraindo: {file_path.name}"
                
                ext = file_path.suffix.lower()

                # Cria pasta de destino dedicada no mesmo diretório do arquivo compactado
                dest_folder = file_path.parent / file_path.stem
                
                # Trata colisão de pastas de destino duplicadas
                counter = 1
                base_folder_name = dest_folder.name
                while dest_folder.exists():
                    dest_folder = file_path.parent / f"{base_folder_name}_{counter}"
                    counter += 1
                
                try:
                    dest_folder.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.log(f"ERRO ao criar pasta de destino {dest_folder.name}: {e}")
                    errors_total += 1
                    continue
                
                try:
                    # ESTRATÉGIA DE EXTRAÇÃO HÍBRIDA
                    if caminho_7z:
                        # Extração via 7-Zip (Suporta 100% dos formatos e algoritmos de compressão)
                        comando = [
                            str(caminho_7z), "x",
                            str(file_path),
                            f"-o{dest_folder}",
                            "-y"
                        ]
                        process = subprocess.run(
                            comando,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            creationflags=0x08000000  # CREATE_NO_WINDOW (Oculta tela preta do CMD)
                        )
                        if process.returncode != 0:
                            raise RuntimeError(f"O 7-Zip falhou com código de retorno: {process.returncode}")
                    else:
                        # Fallback nativo do Python caso o 7-Zip não esteja instalado
                        if ext == '.zip' and zipfile:
                            with zipfile.ZipFile(str(file_path), 'r') as zip_ref:
                                zip_ref.extractall(str(dest_folder))
                        elif ext == '.rar' and rarfile:
                            with rarfile.RarFile(str(file_path), 'r') as rar_ref:
                                rar_ref.extractall(str(dest_folder))
                        elif ext == '.7z' and py7zr:
                            with py7zr.SevenZipFile(str(file_path), 'r') as sz_ref:
                                sz_ref.extractall(str(dest_folder))
                        elif ext in ['.tar', '.gz', '.tgz', '.bz2', '.tbz2', '.xz', '.txz'] and tarfile:
                            with tarfile.open(str(file_path), 'r') as tar_ref:
                                tar_ref.extractall(str(dest_folder))
                        else:
                            raise NotImplementedError(f"Formato não suportado nativamente ou biblioteca ausente: {ext}")

                    # Varredura interna para contar arquivos válidos e limpar lixo do Mac ('._')
                    num_files = 0
                    for root_dir, dirs, files_in_dir in os.walk(str(dest_folder), topdown=False):
                        for f in files_in_dir:
                            f_path = Path(root_dir) / f
                            if f.startswith('._'):
                                try:
                                    os.remove(str(f_path))
                                except:
                                    pass
                            else:
                                num_files += 1
                        # Remove subpastas vazias que possam ter sobrado após a limpeza de '._'
                        for d in dirs:
                            d_path = Path(root_dir) / d
                            try:
                                if not os.listdir(str(d_path)):
                                    os.rmdir(str(d_path))
                            except:
                                pass
                    
                    extracted_total += num_files
                    self.log(f"Sucesso: Extraídos {num_files} arquivos para '{dest_folder.name}'")
                    
                    # Organização: Move o arquivo compactado antigo para '00_COMPACTADOS' na raiz
                    compactados_dir.mkdir(exist_ok=True)
                    dest_archive = compactados_dir / file_path.name
                    
                    # Trata duplicados na pasta de compactados antigos
                    counter = 1
                    base_archive = dest_archive.stem
                    suffix_archive = dest_archive.suffix
                    while dest_archive.exists():
                        dest_archive = compactados_dir / f"{base_archive}_{counter}{suffix_archive}"
                        counter += 1
                    
                    try:
                        os.rename(str(file_path), str(dest_archive))
                    except OSError:
                        shutil.move(str(file_path), str(dest_archive))
                        
                    self.log(f"Movido original: {file_path.name} -> 00_COMPACTADOS/{dest_archive.name}")
                    
                except Exception as e:
                    errors_total += 1
                    self.log(f"ERRO ao processar {file_path.name}: {e}")
                    # Em caso de falha completa, remove a pasta de destino para não deixar lixo incompleto
                    shutil.rmtree(str(dest_folder), ignore_errors=True)
                
                # Atualiza progresso e estatísticas de forma dinâmica
                self.ui_progresso = processed_count / total_discovered if total_discovered > 0 else 1.0
                self.ui_stats_text = f"Arquivos Processados: {processed_count}/{total_discovered} | Extraídos: {extracted_total} | Erros: {errors_total}"

            # Resumo Final no Terminal
            duracao = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
            self.log("\n" + "="*40)
            self.log("RESUMO FINAL DA EXTRAÇÃO")
            self.log(f"Duração Total: {duracao}")
            self.log(f"Pacotes Processados: {processed_count}")
            self.log(f"Total de Arquivos Extraídos: {extracted_total}")
            self.log(f"Erros Encontrados: {errors_total}")
            self.log(f"Compactados antigos movidos para: {compactados_dir.name}/")
            self.log("="*40)
            
        except Exception as e:
            self.log(f"ERRO CRÍTICO NO PROCESSO: {e}")
        finally:
            self.finalizar()

    def worker_mover(self):
        """Thread dedicada para apenas mover os arquivos compactados das subpastas para a raiz."""
        try:
            self.log("Iniciando varredura para mover arquivos compactados...")
            self.start_time = time.time()
            
            compactados_dir = self.root_dir / "00_COMPACTADOS"
            compactados_dir.mkdir(exist_ok=True)
            
            # Varredura inicial para mapear todos os arquivos compactados nas subpastas
            arquivos_para_mover = []
            for root, dirs, files in os.walk(str(self.root_dir)):
                if self.stop_requested:
                    break
                # Ignora a própria pasta de destino e ocultas
                if "00_COMPACTADOS" in root or f"{os.sep}." in root:
                    continue
                for f in files:
                    if not f.startswith(".") and not f.startswith("._"):
                        ext = os.path.splitext(f)[1].lower()
                        if ext in self.compressed_extensions:
                            arquivos_para_mover.append(Path(root) / f)
            
            total_arquivos = len(arquivos_para_mover)
            self.log(f"Varredura concluída! Encontrados {total_arquivos} arquivos compactados para mover.")
            
            if total_arquivos == 0:
                self.log("Nenhum arquivo compactado encontrado nas subpastas.")
                return
                
            movidos = 0
            erros = 0
            
            for idx, file_path in enumerate(arquivos_para_mover, 1):
                if self.stop_requested:
                    break
                while self.pausado and not self.stop_requested:
                    time.sleep(0.1)
                    
                try:
                    rel_path = file_path.relative_to(self.root_dir)
                except ValueError:
                    rel_path = file_path.name
                self.log(f"-> Movendo ({idx}/{total_arquivos}): {rel_path}")
                self.ui_status_text = f"Movendo: {file_path.name}"
                
                dest_file = compactados_dir / file_path.name
                
                # Trata duplicados na pasta de destino
                counter = 1
                base_name = dest_file.stem
                suffix = dest_file.suffix
                while dest_file.exists():
                    dest_file = compactados_dir / f"{base_name}_{counter}{suffix}"
                    counter += 1
                    
                try:
                    # Move o arquivo
                    try:
                        os.rename(str(file_path), str(dest_file))
                    except OSError:
                        shutil.move(str(file_path), str(dest_file))
                    movidos += 1
                except Exception as e:
                    erros += 1
                    self.log(f"ERRO ao mover {file_path.name}: {e}")
                    
                # Atualiza progresso e estatísticas
                self.ui_progresso = idx / total_arquivos
                elapsed = time.time() - self.start_time
                tempo_decorrido = time.strftime("%M:%S", time.gmtime(elapsed))
                self.ui_stats_text = f"Arquivos Processados: {idx}/{total_arquivos} | Movidos: {movidos} | Erros: {erros}"
                
            # Resumo Final
            duracao = time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))
            self.log("\n" + "="*40)
            self.log("RESUMO FINAL DA MOVIMENTAÇÃO")
            self.log(f"Duração Total: {duracao}")
            self.log(f"Arquivos Movidos com Sucesso: {movidos}")
            self.log(f"Erros Encontrados: {erros}")
            self.log(f"Arquivos organizados em: {compactados_dir.name}/")
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

        # Libera controles de navegação e inputs
        self.btn_start.configure(state="normal")
        self.btn_move_only.configure(state="normal")
        self.btn_folder.configure(state="normal")
        self.btn_pause.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        
        if hasattr(self.master.master, 'btn_menu'):
            self.master.master.btn_menu.configure(state="normal")
            
        messagebox.showinfo("Fim", "Processo finalizado.")