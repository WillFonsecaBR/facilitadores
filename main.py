import tkinter as tk
from tkinter import ttk, messagebox
import os

# Importações dos seus scripts (pasta src deve estar no mesmo local)
# from src.organizador import run_organizador
# ... (descomente conforme for integrando)

class AppFacilitadores:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema Facilitadores - Desktop")
        self.root.geometry("1000x650")
        self.root.configure(bg="#2b2b2b") # Fundo escuro

        # Estilização básica para botões e labels
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Menu.TFrame", background="#1e1e1e")
        self.style.configure("Card.TFrame", background="#333333", relief="raised")
        self.style.configure("TButton", font=("Arial", 10, "bold"))

        # Layout Principal
        self.sidebar = tk.Frame(self.root, width=200, bg="#1e1e1e", padx=10, pady=20)
        self.sidebar.pack(side="left", fill="y")

        self.logo = tk.Label(self.sidebar, text="FACILITADORES", fg="white", bg="#1e1e1e", font=("Arial", 14, "bold"))
        self.logo.pack(pady=(0, 30))

        self.btn_home = tk.Button(self.sidebar, text="Menu Principal", command=self.show_main_menu, 
                                  bg="#4a4a4a", fg="white", relief="flat", height=2)
        self.btn_home.pack(fill="x", pady=5)

        self.btn_sair = tk.Button(self.sidebar, text="Sair", command=self.root.quit, 
                                  bg="#c0392b", fg="white", relief="flat", height=2)
        self.btn_sair.pack(side="bottom", fill="x")

        # Área de Conteúdo Dinâmico
        self.container = tk.Frame(self.root, bg="#2b2b2b")
        self.container.pack(side="right", expand=True, fill="both", padx=20, pady=20)

        self.show_main_menu()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_main_menu(self):
        self.clear_container()
        
        # Título
        lbl = tk.Label(self.container, text="Selecione uma Ferramenta", fg="white", bg="#2b2b2b", font=("Arial", 16, "bold"))
        lbl.pack(pady=(0, 20))

        # Grid de Opções
        grid_frame = tk.Frame(self.container, bg="#2b2b2b")
        grid_frame.pack(expand=True, fill="both")

        opcoes = [
            "Organizar Mídias", "Separar Vídeos", "Extrair Arquivos",
            "Selecionar Imagens", "Criar Pastas", "Organizador Edição",
            "Marca D'água", "Renomear Arquivos", "Packs de Vídeos"
        ]

        for i, nome in enumerate(opcoes):
            card = tk.Frame(grid_frame, bg="#333333", padx=20, pady=20, highlightbackground="#4a4a4a", highlightthickness=1)
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
            
            tk.Label(card, text=nome, fg="white", bg="#333333", font=("Arial", 11, "bold")).pack(pady=(0, 15))
            
            btn = tk.Button(card, text="ABRIR", bg="#3498db", fg="white", relief="flat", width=10,
                            command=lambda n=nome: self.abrir_programa(n))
            btn.pack()

        # Ajuste de peso das colunas para centralizar
        for i in range(3):
            grid_frame.grid_columnconfigure(i, weight=1)

    def abrir_programa(self, nome_programa):
        self.clear_container()
        
        # Cabeçalho
        header = tk.Frame(self.container, bg="#2b2b2b")
        header.pack(fill="x", pady=(0, 20))

        btn_voltar = tk.Button(header, text="← VOLTAR", command=self.show_main_menu, bg="#7f8c8d", fg="white", relief="flat")
        btn_voltar.pack(side="left")

        tk.Label(header, text=nome_programa.upper(), fg="white", bg="#2b2b2b", font=("Arial", 14, "bold")).pack(side="left", padx=20)

        # Console de Log Interno
        self.txt_log = tk.Text(self.container, bg="#1e1e1e", fg="#2ecc71", font=("Courier", 10), padx=10, pady=10)
        self.txt_log.pack(expand=True, fill="both")
        self.txt_log.insert("end", f"Sistema pronto para iniciar: {nome_programa}\n\n")

        # Botão de Ação
        btn_run = tk.Button(self.container, text=f"EXECUTAR {nome_programa.upper()}", 
                            bg="#27ae60", fg="white", font=("Arial", 12, "bold"), pady=10,
                            command=lambda: self.escrever_log(f"Iniciando processo de {nome_programa}..."))
        btn_run.pack(fill="x", pady=(20, 0))

    def escrever_log(self, mensagem):
        self.txt_log.insert("end", f"> {mensagem}\n")
        self.txt_log.see("end")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppFacilitadores(root)
    root.mainloop()