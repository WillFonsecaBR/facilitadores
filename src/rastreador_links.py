"""
FERRAMENTA: RASTREADOR DE LINKS (FACILITADORES)
LÓGICA:
1. SCRAPING: Acessa a URL e identifica todos os links de download e tamanhos.
2. ANÁLISE: Extrai o tamanho do arquivo (KB/MB/GB) via Regex.
3. PLANILHA: Gera obrigatoriamente um arquivo Excel (.xlsx) com a lista completa.
4. DIRETÓRIO OBRIGATÓRIO: O software EXIGE que o usuário escolha o local e o nome do arquivo antes de iniciar o processamento.
5. RELATÓRIO: Soma o tamanho total e converte para GB no terminal.
"""

import os
import re
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pandas as pd
import requests
from bs4 import BeautifulSoup


class RastreadorLinksFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.is_running = False
        self.stop_requested = False
        self.save_path = ""
        self.setup_ui()

    def setup_ui(self):
        self.configure(fg_color="transparent")
        ctk.CTkLabel(self, text="RASTREADOR DE LINKS & VOLUMETRIA", font=("Segoe UI", 20, "bold")).pack(pady=(10, 20))

        config_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        config_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(config_frame, text="URL do Site:").grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        self.entry_url = ctk.CTkEntry(config_frame, placeholder_text="https://exemplo.com/lista.html", height=35, fg_color="#0f0f0f", width=500)
        self.entry_url.grid(row=0, column=1, padx=15, pady=(15, 5), sticky="ew")

        ctk.CTkLabel(config_frame, text="Salvar em:").grid(row=1, column=0, padx=15, pady=(5, 15), sticky="w")
        folder_subframe = ctk.CTkFrame(config_frame, fg_color="transparent")
        folder_subframe.grid(row=1, column=1, padx=15, pady=(5, 15), sticky="ew")
        
        self.btn_select_path = ctk.CTkButton(folder_subframe, text="📁 SELECIONAR PASTA", command=self.select_folder, fg_color="#3d3d3d", width=150)
        self.btn_select_path.pack(side="left")
        
        self.lbl_save_path = ctk.CTkLabel(folder_subframe, text="Nenhuma pasta selecionada", text_color="gray")
        self.lbl_save_path.pack(side="left", padx=10)

        self.terminal = ctk.CTkTextbox(self, height=280, font=("Courier New", 12), fg_color="#000000", text_color="#3498db")
        self.terminal.pack(fill="both", padx=20, pady=10)

        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=20)
        self.status_frame.grid_columnconfigure((0,1,2), weight=1)
        self.lbl_count = ctk.CTkLabel(self.status_frame, text="Links Coletados: 0")
        self.lbl_count.grid(row=0, column=0, sticky="w")
        self.lbl_size = ctk.CTkLabel(self.status_frame, text="Tamanho Total: 0 GB", text_color="#2ecc71")
        self.lbl_size.grid(row=0, column=1)

        self.progress_bar = ctk.CTkProgressBar(self, width=800, progress_color="#3498db")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=15)

        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.pack(pady=10)
        self.btn_start = ctk.CTkButton(self.ctrl_frame, text="▶ INICIAR RASTREIO", fg_color="#2ecc71", width=250, height=45, font=("Segoe UI", 13, "bold"), command=self.iniciar)
        self.btn_start.grid(row=0, column=0, padx=10)
        self.btn_stop = ctk.CTkButton(self.ctrl_frame, text="PARAR", fg_color="#e74c3c", width=120, height=45, state="disabled", command=self.stop)
        self.btn_stop.grid(row=0, column=1, padx=10)

    def log(self, msg):
        self.terminal.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.terminal.see("end")

    def select_folder(self):
        path = filedialog.askdirectory(title="Selecione a pasta para salvar o Excel")
        if path:
            self.save_path = Path(path)
            self.lbl_save_path.configure(text=str(self.save_path), text_color="white")

    def stop(self):
        self.stop_requested = True
        self.log("Solicitando parada...")

    def converter_tamanho(self, texto_tamanho):
        texto = texto_tamanho.upper().replace(",", ".")
        try:
            numero = float(re.findall(r"[-+]?\d*\.\d+|\d+", texto)[0])
            if "G" in texto: return numero * 1024**3
            if "M" in texto: return numero * 1024**2
            if "K" in texto: return numero * 1024
            return numero
        except: return 0

    def iniciar(self):
        url = self.entry_url.get().strip()
        if not url.startswith("http"):
            messagebox.showwarning("Aviso", "Insira uma URL válida.")
            return
        if not self.save_path:
            messagebox.showwarning("Aviso", "Selecione a PASTA DE DESTINO primeiro.")
            return

        self.is_running = True
        self.stop_requested = False
        self.btn_start.configure(state="disabled")
        self.btn_select_path.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.terminal.delete("1.0", "end")
        threading.Thread(target=self.worker, args=(url,), daemon=True).start()

    def worker(self, url):
        nome_arquivo = f"Rastreio_{int(time.time())}.xlsx"
        caminho_final = self.save_path / nome_arquivo
        self.log(f"Iniciando. O arquivo será salvo em: {caminho_final}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            self.log(f"ERRO DE CONEXÃO: {e}")
            self.finalizar()
            return

        dados_coletados = []
        tamanho_total_bytes = 0
        links = soup.find_all('a', href=True)
        total_links = len(links)
        
        for i, link in enumerate(links, 1):
            if self.stop_requested: break
            href = link['href']
            if href.startswith('#') or 'javascript:' in href: continue
            
            texto_completo = link.get_text() + " " + (link.parent.get_text() if link.parent else "")
            padrao_tamanho = re.findall(r'\d+[\.,]?\d*\s?[KMGB]B?', texto_completo, re.IGNORECASE)
            tamanho_str = padrao_tamanho[0] if padrao_tamanho else "Desconhecido"
            
            bytes_arq = self.converter_tamanho(tamanho_str)
            tamanho_total_bytes += bytes_arq
            
            dados_coletados.append({
                "Nome/Texto": link.get_text().strip(),
                "URL": href if href.startswith("http") else url + href,
                "Tamanho": tamanho_str
            })

            if i % 10 == 0 or i == total_links:
                self.progress_bar.set(i / total_links)
                self.lbl_count.configure(text=f"Links Coletados: {len(dados_coletados)}")
                self.lbl_size.configure(text=f"Tamanho Total: {tamanho_total_bytes / (1024**3):.2f} GB")

        if dados_coletados and not self.stop_requested:
            try:
                df = pd.DataFrame(dados_coletados)
                df.to_excel(caminho_final, index=False)
                self.log(f"SUCESSO: Arquivo salvo em {caminho_final}")
            except Exception as e:
                self.log(f"ERRO AO SALVAR: {e}")

        self.log("\n" + "="*40)
        self.log("RELATÓRIO DE RASTREIO")
        self.log(f"Total de Links: {len(dados_coletados)}")
        self.log(f"Volume Total: {tamanho_total_bytes / (1024**3):.2f} GB")
        self.log("="*40)
        self.finalizar()

    def finalizar(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_select_path.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        messagebox.showinfo("Fim", "Processo finalizado.")