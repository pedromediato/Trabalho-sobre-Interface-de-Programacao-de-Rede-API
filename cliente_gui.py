"""
cliente_gui.py - PyChat Ultra Modern (Com Sombras Projetadas)

Correção aplicada:
- Parâmetros 'width' e 'height' ajustados para o construtor do CTkFrame.
"""

import socket
import threading
import json
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox

# Configurações globais do tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- PALETA DE CORES ---
COR_FUNDO_PRINCIPAL = "#0B0B10"  # Fundo ultra escuro
COR_SOMBRA_DIFUSA   = "#040407"  # Sombra difusa
COR_SOMBRA_DENSA    = "#07070C"  # Sombra concentrada
COR_PAINEL          = "#1A1A26"  # Card/Painel
COR_INPUT           = "#232334"  # Inputs
COR_TEXTO           = "#E0E0E0"  # Texto principal
COR_AZUL_ACCENT     = "#5865F2"  # Destaque
COR_HOVER_AZUL      = "#4752C4"  # Hover
COR_VERDE_VOCE      = "#57F287"  # Mensagens [Você]
COR_ROSA_PRIVADO    = "#EB459E"  # Mensagens privadas
COR_AMARELO_SISTEMA = "#FEE75C"  # Avisos de sistema


class ChatClienteGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.sock = None
        self.conectado = False
        self.apelido = ""

        # Configuração da Janela
        self.title("PyChat - Deluxe Edition")
        self.geometry("850x650")
        self.configure(fg_color=COR_FUNDO_PRINCIPAL)
        self.protocol("WM_DELETE_WINDOW", self.fechar_conexao)

        self.criar_tela_login()

    # =========================================================================
    # 1. TELA DE LOGIN (Card com Sombra Projetada)
    # =========================================================================
    def criar_tela_login(self):
        # Container transparente central com dimensões no construtor
        self.container_login = ctk.CTkFrame(
            self, 
            fg_color="transparent", 
            width=420, 
            height=480
        )
        self.container_login.place(relx=0.5, rely=0.5, anchor="center")

        # 🔴 CAMADA DE SOMBRA 2 (Difusa/Extensa)
        sombra_difusa = ctk.CTkFrame(
            self.container_login,
            fg_color=COR_SOMBRA_DIFUSA,
            corner_radius=24,
            border_width=0
        )
        sombra_difusa.place(relx=0.52, rely=0.52, anchor="center", relwidth=0.92, relheight=0.92)

        # 🔴 CAMADA DE SOMBRA 1 (Densa/Próxima)
        sombra_densa = ctk.CTkFrame(
            self.container_login,
            fg_color=COR_SOMBRA_DENSA,
            corner_radius=22,
            border_width=0
        )
        sombra_densa.place(relx=0.51, rely=0.51, anchor="center", relwidth=0.91, relheight=0.91)

        # 🟢 CARD PRINCIPAL
        self.frame_login = ctk.CTkFrame(
            self.container_login,
            fg_color=COR_PAINEL,
            corner_radius=20,
            border_width=1,
            border_color="#2E2E45"
        )
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.9)

        # Conteúdo do Login
        ctk.CTkLabel(
            self.frame_login,
            text="⚡ PyChat",
            font=("Segoe UI", 24, "bold"),
            text_color=COR_AZUL_ACCENT
        ).pack(pady=(25, 15))

        self.ent_host = self._criar_campo_input("IP do Servidor:", "127.0.0.1")
        self.ent_porta = self._criar_campo_input("Porta:", "8080")
        self.ent_apelido = self._criar_campo_input("Seu Apelido:", "")

        btn_conectar = ctk.CTkButton(
            self.frame_login,
            text="Entrar no Chat",
            font=("Segoe UI", 12, "bold"),
            fg_color=COR_AZUL_ACCENT,
            hover_color=COR_HOVER_AZUL,
            height=42,
            corner_radius=12,
            command=self.conectar_ao_servidor
        )
        btn_conectar.pack(pady=(20, 20), padx=30, fill="x")

    def _criar_campo_input(self, label_text, default_value):
        frame = ctk.CTkFrame(self.frame_login, fg_color="transparent")
        frame.pack(fill="x", pady=5, padx=30)

        ctk.CTkLabel(frame, text=label_text, font=("Segoe UI", 11), text_color="#A0A0B8").pack(anchor="w")
        entry = ctk.CTkEntry(
            frame,
            font=("Segoe UI", 12),
            fg_color=COR_INPUT,
            border_color="#2E2E45",
            corner_radius=10,
            height=36
        )
        entry.insert(0, default_value)
        entry.pack(fill="x", pady=(2, 0))
        return entry

    def conectar_ao_servidor(self):
        host = self.ent_host.get().strip()
        porta_str = self.ent_porta.get().strip()
        self.apelido = self.ent_apelido.get().strip()

        if not host or not porta_str or not self.apelido:
            messagebox.showwarning("Aviso", "Por favor, preencha todos os campos!")
            return

        try:
            porta = int(porta_str)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, porta))

            pacote_conexao = json.dumps({"tipo": "conexao", "apelido": self.apelido}) + "\n"
            self.sock.sendall(pacote_conexao.encode("utf-8"))

            self.conectado = True
            self.container_login.destroy()
            self.criar_tela_chat()

            thread_receber = threading.Thread(target=self.receber_mensagens, daemon=True)
            thread_receber.start()

        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao servidor:\n{e}")

    # =========================================================================
    # 2. TELA DE CHAT
    # =========================================================================
    def criar_tela_chat(self):
        # Top Bar
        frame_topo_sombra = ctk.CTkFrame(self, fg_color=COR_SOMBRA_DENSA, corner_radius=16, height=52)
        frame_topo_sombra.pack(fill="x", padx=15, pady=(15, 0))

        frame_topo = ctk.CTkFrame(frame_topo_sombra, fg_color=COR_PAINEL, corner_radius=15, height=50, border_width=1, border_color="#2E2E45")
        frame_topo.pack(fill="both", expand=True, padx=1, pady=1)

        ctk.CTkLabel(
            frame_topo,
            text=f"● Conectado como: {self.apelido}",
            font=("Segoe UI", 13, "bold"),
            text_color=COR_VERDE_VOCE
        ).pack(side="left", padx=20, pady=10)

        # Corpo
        frame_corpo = ctk.CTkFrame(self, fg_color="transparent")
        frame_corpo.pack(fill="both", expand=True, padx=15, pady=12)

        # Sombra da Caixa do Chat
        sombra_chat = ctk.CTkFrame(frame_corpo, fg_color=COR_SOMBRA_DENSA, corner_radius=16)
        sombra_chat.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.area_chat = ctk.CTkTextbox(
            sombra_chat,
            font=("Consolas", 12),
            fg_color=COR_PAINEL,
            text_color=COR_TEXTO,
            corner_radius=15,
            border_width=1,
            border_color="#2E2E45",
            wrap="word"
        )
        self.area_chat.pack(fill="both", expand=True, padx=1, pady=1)
        self.area_chat.configure(state="disabled")

        self.area_chat._textbox.tag_config("voce", foreground=COR_VERDE_VOCE, font=("Consolas", 12, "bold"))
        self.area_chat._textbox.tag_config("normal", foreground="#89B4FA")
        self.area_chat._textbox.tag_config("privado", foreground=COR_ROSA_PRIVADO, font=("Consolas", 12, "bold"))
        self.area_chat._textbox.tag_config("sistema", foreground=COR_AMARELO_SISTEMA, font=("Consolas", 11, "italic"))

        # Sombra da Sidebar
        sombra_sidebar = ctk.CTkFrame(frame_corpo, fg_color=COR_SOMBRA_DENSA, width=200, corner_radius=16)
        sombra_sidebar.pack(side="right", fill="y")
        sombra_sidebar.pack_propagate(False)

        self.frame_sidebar = ctk.CTkFrame(sombra_sidebar, fg_color=COR_PAINEL, corner_radius=15, border_width=1, border_color="#2E2E45")
        self.frame_sidebar.pack(fill="both", expand=True, padx=1, pady=1)
        self.frame_sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.frame_sidebar,
            text="ONLINE",
            font=("Segoe UI", 11, "bold"),
            text_color="#80809D"
        ).pack(anchor="w", padx=15, pady=(15, 5))

        self.scroll_usuarios = ctk.CTkScrollableFrame(self.frame_sidebar, fg_color="transparent")
        self.scroll_usuarios.pack(fill="both", expand=True, padx=5, pady=5)

        # Rodapé
        sombra_rodape = ctk.CTkFrame(self, fg_color=COR_SOMBRA_DENSA, corner_radius=26, height=48)
        sombra_rodape.pack(fill="x", padx=15, pady=(0, 15))

        frame_rodape = ctk.CTkFrame(sombra_rodape, fg_color="transparent")
        frame_rodape.pack(fill="both", expand=True)

        self.ent_mensagem = ctk.CTkEntry(
            frame_rodape,
            placeholder_text="Digite sua mensagem...",
            font=("Segoe UI", 12),
            fg_color=COR_PAINEL,
            border_color="#2E2E45",
            corner_radius=25,
            height=46
        )
        self.ent_mensagem.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.ent_mensagem.bind("<Return>", lambda event: self.enviar_mensagem())

        btn_enviar = ctk.CTkButton(
            frame_rodape,
            text="Enviar",
            font=("Segoe UI", 12, "bold"),
            fg_color=COR_AZUL_ACCENT,
            hover_color=COR_HOVER_AZUL,
            corner_radius=25,
            width=110,
            height=46,
            command=self.enviar_mensagem
        )
        btn_enviar.pack(side="right")

    # =========================================================================
    # 3. LÓGICA DE FUNCIONAMENTO
    # =========================================================================
    def adicionar_texto_chat(self, texto, tag="normal"):
        def _inserir():
            self.area_chat.configure(state="normal")
            self.area_chat._textbox.insert("end", texto + "\n", tag)
            self.area_chat.see("end")
            self.area_chat.configure(state="disabled")

        self.after(0, _inserir)

    def enviar_mensagem(self):
        texto = self.ent_mensagem.get().strip()
        if not texto or not self.conectado:
            return

        try:
            pacote = json.dumps({"tipo": "mensagem", "texto": texto}) + "\n"
            self.sock.sendall(pacote.encode("utf-8"))
            self.ent_mensagem.delete(0, "end")

            hora = datetime.now().strftime("%H:%M")
            if not texto.startswith("/"):
                self.adicionar_texto_chat(f"[{hora}] [Você]: {texto}", tag="voce")

        except Exception as e:
            self.adicionar_texto_chat(f"[ERRO]: Falha ao enviar mensagem: {e}", tag="sistema")

    def receber_mensagens(self):
        buffer_dados = ""
        while self.conectado:
            try:
                dados_brutos = self.sock.recv(2048).decode("utf-8")
                if not dados_brutos:
                    self.adicionar_texto_chat("[SISTEMA]: Você foi desconectado pelo servidor.", tag="sistema")
                    self.conectado = False
                    break

                buffer_dados += dados_brutos
                while "\n" in buffer_dados:
                    linha_json, buffer_dados = buffer_dados.split("\n", 1)
                    if not linha_json.strip():
                        continue

                    pacote = json.loads(linha_json)
                    tipo = pacote.get("tipo")

                    if tipo == "mensagem":
                        hora = pacote.get("hora", "")
                        remetente = pacote.get("remetente", "")
                        texto = pacote.get("texto", "")
                        self.adicionar_texto_chat(f"[{hora}] [{remetente}]: {texto}", tag="normal")

                    elif tipo == "msg_privada":
                        hora = pacote.get("hora", "")
                        remetente = pacote.get("remetente", "")
                        texto = pacote.get("texto", "")
                        self.adicionar_texto_chat(f"[{hora}] [PRIVADO de {remetente}]: {texto}", tag="privado")

                    elif tipo == "sistema":
                        self.adicionar_texto_chat(f"[SISTEMA]: {pacote.get('texto')}", tag="sistema")

                    elif tipo == "lista_usuarios":
                        usuarios = pacote.get("usuarios", [])
                        self.after(0, lambda u=usuarios: self.atualizar_lista_usuarios(u))

            except Exception as e:
                if self.conectado:
                    self.adicionar_texto_chat(f"[ERRO DE REDE]: {e}", tag="sistema")
                break

    def atualizar_lista_usuarios(self, lista):
        for widget in self.scroll_usuarios.winfo_children():
            widget.destroy()

        for user in lista:
            e_voce = user == self.apelido
            texto = f"• {user} (Você)" if e_voce else f"• {user}"
            cor_texto = COR_VERDE_VOCE if e_voce else COR_TEXTO

            lbl = ctk.CTkLabel(
                self.scroll_usuarios,
                text=texto,
                text_color=cor_texto,
                font=("Segoe UI", 12, "bold" if e_voce else "normal")
            )
            lbl.pack(anchor="w", pady=3, padx=5)

    def fechar_conexao(self):
        if self.conectado and self.sock:
            try:
                pacote = json.dumps({"tipo": "mensagem", "texto": "sair"}) + "\n"
                self.sock.sendall(pacote.encode("utf-8"))
            except:
                pass
            self.conectado = False
            self.sock.close()
        self.destroy()


if __name__ == "__main__":
    app = ChatClienteGUI()
    app.mainloop()