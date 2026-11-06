"""
LIMPADOR DE URLS INSTAGRAM 2.0 - VERSÃO AUDITORIA TOTAL
CORREÇÕES APLICADAS:
- Limpeza de Padrão (Passo 1): Remoção obrigatória de '?igsh=' e rastreios via Regex + Split.
- Trava de Segurança: Bloqueio de início caso nenhum nicho válido esteja selecionado.
- Manutenção de Integridade: Nenhuma outra funcionalidade ou estilo foi alterado.
"""

import os
import re
import threading
import time
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk


class LimpadorUrlsFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Caminho para o banco de dados
        self.db_path = Path(__file__).parent.parent / "database_links" / "INSTAGRAM"
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.is_running = False
        self.foi_copiado = False 
        
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")

        # --- HEADER ---
        header = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=12)
        header.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(header, text="LIMPADOR DE URLS 2.0", font=("Segoe UI", 20, "bold")).pack(side="left", padx=20, pady=15)
        
        # Carregar Nichos
        nichos = [f.stem for f in self.db_path.glob("*.txt")]
        if not nichos: nichos = ["Crie um arquivo .txt em database_links/INSTAGRAM"]
        
        self.combo_nicho = ctk.CTkComboBox(header, values=nichos, width=250, height=35)
        self.combo_nicho.pack(side="right", padx=20)
        ctk.CTkLabel(header, text="Nicho:").pack(side="right", padx=5)

        # --- ÁREAS DE TEXTO ---
        text_container = ctk.CTkFrame(self, fg_color="transparent")
        text_container.pack(fill="both", expand=True, padx=10)
        text_container.grid_columnconfigure((0, 1, 2), weight=1)

        # 1. Entrada
        col1 = ctk.CTkFrame(text_container, fg_color="transparent")
        col1.grid(row=0, column=0, sticky="nsew", padx=5)
        ctk.CTkLabel(col1, text="1. COLE AS URLS", font=("Segoe UI", 12, "bold")).pack(pady=5)
        self.txt_entrada = ctk.CTkTextbox(col1, fg_color="#000", text_color="#fff", font=("Consolas", 11))
        self.txt_entrada.pack(fill="both", expand=True)

        # 2. Duplicadas / Banco
        col2 = ctk.CTkFrame(text_container, fg_color="transparent")
        col2.grid(row=0, column=1, sticky="nsew", padx=5)
        ctk.CTkLabel(col2, text="2. DUPLICADAS / NO BANCO", font=("Segoe UI", 12, "bold"), text_color="#e74c3c").pack(pady=5)
        self.txt_duplicadas = ctk.CTkTextbox(col2, fg_color="#000", text_color="#e74c3c", font=("Consolas", 11), state="disabled")
        self.txt_duplicadas.pack(fill="both", expand=True)

        # 3. Limpas
        col3 = ctk.CTkFrame(text_container, fg_color="transparent")
        col3.grid(row=0, column=2, sticky="nsew", padx=5)
        ctk.CTkLabel(col3, text="3. URLS LIMPAS", font=("Segoe UI", 12, "bold"), text_color="#2ecc71").pack(pady=5)
        self.txt_limpas = ctk.CTkTextbox(col3, fg_color="#000", text_color="#2ecc71", font=("Consolas", 11), state="disabled")
        self.txt_limpas.pack(fill="both", expand=True)
        
        self.btn_copy = ctk.CTkButton(col3, text="COPIAR LIMPAS", fg_color="#2ecc71", text_color="#000", 
                                       font=("Segoe UI", 12, "bold"), command=self.copiar_limpas)
        self.btn_copy.pack(pady=10, fill="x")

        # --- STATUS E CONTROLES ---
        self.progress_bar = ctk.CTkProgressBar(self, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=10)

        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(ctrl_frame, text="INICIAR LIMPEZA", fg_color="#3498db", 
                                       width=180, height=40, font=("Segoe UI", 13, "bold"),
                                       command=self.iniciar_processo)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_add_db = ctk.CTkButton(ctrl_frame, text="ADICIONAR AO BANCO", fg_color="#3d3d3d", 
                                        width=180, height=40, font=("Segoe UI", 13, "bold"),
                                        command=self.adicionar_ao_banco)
        self.btn_add_db.grid(row=0, column=1, padx=10)

        self.btn_clear = ctk.CTkButton(ctrl_frame, text="LIMPAR TUDO", fg_color="#c0392b", hover_color="#e74c3c",
                                        width=180, height=40, font=("Segoe UI", 13, "bold"),
                                        command=self.limpar_tudo)
        self.btn_clear.grid(row=0, column=2, padx=10)

    def normalizar_url(self, texto):
        """PASSO 1: Extrai e remove obrigatoriamente o padrão ?igsh= e rastreios."""
        # Regex para capturar a URL base do Instagram ignorando parâmetros após ? ou #
        match = re.search(r'(https?://(?:www\.)?instagram\.com/[^\s?#]+)', texto.lower())
        if match:
            url = match.group(1)
            # Split redundante para garantir a remoção de qualquer resíduo de query string
            url_limpa = url.split("?")[0].split("#")[0].rstrip("/")
            # Padronização de prefixo
            url_limpa = url_limpa.replace("https://www.", "https://")
            return url_limpa
        return ""

    def copiar_limpas(self):
        conteudo = self.txt_limpas.get("1.0", "end-1c")
        if conteudo.strip():
            self.clipboard_clear()
            self.clipboard_append(conteudo)
            self.foi_copiado = True 
            self.btn_copy.configure(text="COPIADO!", fg_color="#27ae60")
            self.after(2000, lambda: self.btn_copy.configure(text="COPIAR LIMPAS", fg_color="#2ecc71"))

    def limpar_tudo(self):
        conteudo_limpas = self.txt_limpas.get("1.0", "end-1c").strip()
        if conteudo_limpas and not self.foi_copiado:
            messagebox.showwarning("Segurança", "Copie os resultados antes de resetar!")
            return
        if messagebox.askyesno("Confirmar", "Limpar todos os campos?"):
            self.txt_entrada.delete("1.0", "end")
            self.txt_duplicadas.configure(state="normal")
            self.txt_duplicadas.delete("1.0", "end")
            self.txt_duplicadas.configure(state="disabled")
            self.txt_limpas.configure(state="normal")
            self.txt_limpas.delete("1.0", "end")
            self.txt_limpas.configure(state="disabled")
            self.progress_bar.set(0)
            self.foi_copiado = False

    def iniciar_processo(self):
        entrada = self.txt_entrada.get("1.0", "end-1c").strip()
        nicho = self.combo_nicho.get()
        
        # TRAVA: Não inicia sem nicho escolhido ou se for o texto de instrução
        if not nicho or "Crie um arquivo" in nicho or nicho.strip() == "":
            messagebox.showwarning("Aviso", "Você deve selecionar um NICHO válido antes de iniciar a limpeza.")
            return

        if not entrada:
            messagebox.showwarning("Aviso", "Cole as URLs primeiro!")
            return

        self.txt_duplicadas.configure(state="normal")
        self.txt_duplicadas.delete("1.0", "end")
        self.txt_limpas.configure(state="normal")
        self.txt_limpas.delete("1.0", "end")
        self.btn_start.configure(state="disabled")
        
        threading.Thread(target=self.worker, args=(entrada, nicho), daemon=True).start()

    def worker(self, texto_entrada, nicho_nome):
        linhas = [l.strip() for l in texto_entrada.split("\n") if l.strip()]
        total = len(linhas)
        
        # Carregamento do banco
        db_file = self.db_path / f"{nicho_nome}.txt"
        banco_dados = set()
        if db_file.exists():
            with open(db_file, "r", encoding="utf-8") as f:
                for line in f:
                    u_limpa = self.normalizar_url(line)
                    if u_limpa: banco_dados.add(u_limpa)

        urls_vistas_sessao = set()
        duplicadas_list = []
        limpas_puras = []
        limpas_com_texto = []
        
        for i, linha in enumerate(linhas, 1):
            url_limpa = self.normalizar_url(linha)
            if not url_limpa: continue
            
            # PRIORIDADE 1: Banco de Dados (❌)
            if url_limpa in banco_dados:
                duplicadas_list.append(f"❌ {linha}")
            
            # PRIORIDADE 2: Duplicada na Lista (❓)
            elif url_limpa in urls_vistas_sessao:
                duplicadas_list.append(f"❓ {linha}")
            
            else:
                urls_vistas_sessao.add(url_limpa)
                # Substitui a URL bruta (com lixo) pela limpa na linha final
                match_orig = re.search(r'(https?://(?:www\.)?instagram\.com/[^\s]+)', linha)
                if match_orig:
                    nova_linha = linha.replace(match_orig.group(0), url_limpa)
                    if linha.strip() == match_orig.group(0).strip():
                        limpas_puras.append(nova_linha)
                    else:
                        limpas_com_texto.append(nova_linha)

            if i % 10 == 0 or i == total: self.progress_bar.set(i / total)

        # Ordenação e Impressão
        limpas_puras.sort()
        limpas_com_texto.sort()

        if duplicadas_list: self.txt_duplicadas.insert("end", "\n".join(duplicadas_list) + "\n")
        if limpas_puras: self.txt_limpas.insert("end", "\n".join(limpas_puras) + "\n")
        if limpas_com_texto: self.txt_limpas.insert("end", "\n".join(limpas_com_texto) + "\n")

        self.txt_duplicadas.configure(state="disabled")
        self.txt_limpas.configure(state="disabled")
        self.btn_start.configure(state="normal")
        messagebox.showinfo("Fim", f"Processamento concluído!\n{len(banco_dados)} links auditados no banco.")

    def adicionar_ao_banco(self):
        nicho = self.combo_nicho.get()
        conteudo = self.txt_limpas.get("1.0", "end-1c").strip()
        if not conteudo: return
        
        if messagebox.askyesno("Confirmar", f"Salvar esses links em '{nicho}.txt'?"):
            db_file = self.db_path / f"{nicho}.txt"
            urls_para_salvar = []
            for linha in conteudo.split("\n"):
                u = self.normalizar_url(linha)
                if u: urls_para_salvar.append(u)
            
            with open(db_file, "a", encoding="utf-8") as f:
                for url in urls_para_salvar: f.write(f"{url}\n")
            messagebox.showinfo("Sucesso", "Links adicionados ao banco!")