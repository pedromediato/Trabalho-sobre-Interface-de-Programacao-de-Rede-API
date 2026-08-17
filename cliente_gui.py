# ==============================================================================
#                 CLIENTE BATE-PAPO - INTERFACE GRÁFICA (GUI)
# ==============================================================================

import socket
import threading
import json
import os
import sys
import subprocess
import base64
import shutil
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox, filedialog, Menu, simpledialog
from PIL import Image, ImageTk

PASTA_ARQUIVOS_RECEBIDOS = "arquivos_recebidos"
TAMANHO_MAXIMO_ARQUIVO_MB = 15
EXTENSOES_IMAGEM = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')


def e_imagem(nome_arquivo):
    """Verifica se o arquivo é uma imagem suportada."""
    return nome_arquivo.lower().endswith(EXTENSOES_IMAGEM)


def abrir_no_sistema(caminho):
    """Abre um arquivo comum no aplicativo padrão do sistema operacional."""
    try:
        if not os.path.exists(caminho):
            messagebox.showerror("Erro", f"Caminho não encontrado:\n{caminho}")
            return
        if os.name == "nt":
            os.startfile(caminho)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho])
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir:\n{e}")


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# PALETA DE CORES DA INTERFACE
COR_FUNDO_PRINCIPAL = "#0D0B10"
COR_PAINEL           = "#1A1A26"
COR_INPUT            = "#232334"
COR_TEXTO            = "#F0F0E0"
COR_AZUL_ACCENT      = "#5865F2"
COR_HOVER_AZUL       = "#4752C4"
COR_VERDE_VOCE       = "#57F287"
COR_AMARELO_SISTEMA  = "#FEE75C"
COR_ROXO_PRIVADO     = "#A5B4FC"

TEXTO_AJUDA = (
    "\n--- 💡 GUIA DE COMANDOS DO CHAT ---\n"
    "• /ajuda             -> Exibe esta lista de ajuda\n"
    "• /clear             -> Limpa a tela desta janela\n"
    "• /apagar <id>       -> Apaga uma mensagem enviada por você pelo ID (ex: /apagar 3)\n"
    "• Clique no Usuário  -> Abre janela de conversa privada\n"
    "-----------------------------------"
)


class ModalImagemDiscord(ctk.CTkToplevel):
    """Visualizador estilo Discord: tela cheia, overlay escuro, info do remetente e opção de download."""
    def __init__(self, parent, caminho_imagem, remetente="", hora=""):
        super().__init__(parent)
        self.caminho_imagem = caminho_imagem
        
        self.attributes("-fullscreen", True)
        self.configure(fg_color="#0B0B0E")
        
        self.transient(parent)
        self.focus_force()
        self.grab_set()

        # Eventos para fechar (ESC ou clicar no fundo escuro)
        self.bind("<Escape>", lambda e: self.fechar())
        self.bind("<Button-1>", lambda e: self.fechar())

        # Informações no Canto Superior Esquerdo
        texto_info = f"Enviado por {remetente} • {hora}" if remetente else ""
        lbl_info = ctk.CTkLabel(
            self,
            text=texto_info,
            font=("Segoe UI", 13, "bold"),
            text_color="#A0A0B8"
        )
        lbl_info.place(relx=0.03, rely=0.04, anchor="nw")
        lbl_info.bind("<Button-1>", lambda e: "break")

        # Imagem Centralizada
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()

            img_pil = Image.open(caminho_imagem)
            max_w = int(screen_w * 0.85)
            max_h = int(screen_h * 0.85)
            img_pil.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

            self.ctk_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=img_pil.size)

            lbl_imagem = ctk.CTkLabel(self, image=self.ctk_img, text="")
            lbl_imagem.place(relx=0.5, rely=0.5, anchor="center")
            lbl_imagem.bind("<Button-1>", lambda e: "break")

        except Exception:
            self.fechar()
            return

        # Botão Baixar Imagem (Canto Superior Direito)
        btn_download = ctk.CTkButton(
            self,
            text="📥 Baixar Imagem",
            font=("Segoe UI", 12, "bold"),
            fg_color="#1E1E28",
            hover_color=COR_AZUL_ACCENT,
            text_color="#FFFFFF",
            height=38,
            corner_radius=10,
            command=self.baixar_imagem
        )
        btn_download.place(relx=0.91, rely=0.04, anchor="e")
        btn_download.bind("<Button-1>", lambda e: "break")

        # Botão Fechar (X)
        btn_fechar = ctk.CTkButton(
            self,
            text="✕",
            font=("Segoe UI", 16, "bold"),
            fg_color="#1E1E28",
            hover_color="#FF4444",
            text_color="#FFFFFF",
            width=38,
            height=38,
            corner_radius=19,
            command=self.fechar
        )
        btn_fechar.place(relx=0.96, rely=0.04, anchor="e")
        btn_fechar.bind("<Button-1>", lambda e: "break")

    def baixar_imagem(self):
        if not os.path.exists(self.caminho_imagem):
            messagebox.showerror("Erro", "Arquivo de imagem não encontrado!")
            return

        nome_original = os.path.basename(self.caminho_imagem)
        extensao = os.path.splitext(nome_original)[1]

        caminho_destino = filedialog.asksaveasfilename(
            title="Salvar Imagem",
            initialfile=nome_original,
            defaultextension=extensao,
            filetypes=[("Arquivos de Imagem", "*.png *.jpg *.jpeg *.gif *.webp *.bmp"), ("Todos os Arquivos", "*.*")]
        )

        if caminho_destino:
            try:
                shutil.copy2(self.caminho_imagem, caminho_destino)
                messagebox.showinfo("Sucesso", "Imagem salva com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar a imagem:\n{e}")

    def fechar(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


class JanelaChatPrivado(ctk.CTkToplevel):
    """Janela popup para conversa privada."""
    def __init__(self, app_principal, destinatario):
        super().__init__(app_principal)
        self.app_principal = app_principal
        self.destinatario = destinatario
        self.referencias_imagens = []

        self.title(f"🔒 Chat Privado com {destinatario}")
        self.geometry("480x520")
        self.configure(fg_color=COR_FUNDO_PRINCIPAL)

        self.protocol("WM_DELETE_WINDOW", self.fechar)

        # Header
        frame_topo = ctk.CTkFrame(self, fg_color=COR_PAINEL, corner_radius=12, height=45)
        frame_topo.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(
            frame_topo, 
            text=f"💬 Chat Privado: {destinatario}", 
            font=("Segoe UI", 13, "bold"), 
            text_color=COR_ROXO_PRIVADO
        ).pack(side="left", padx=15)

        ctk.CTkButton(
            frame_topo,
            text="📂",
            font=("Segoe UI", 13),
            fg_color="transparent",
            hover_color=COR_INPUT,
            width=32,
            height=28,
            command=lambda: abrir_no_sistema(os.path.abspath(PASTA_ARQUIVOS_RECEBIDOS))
        ).pack(side="right", padx=(0, 10))

        self.btn_menu_opcoes = ctk.CTkButton(
            frame_topo,
            text="⋮",
            font=("Segoe UI", 16, "bold"),
            fg_color="transparent",
            hover_color=COR_INPUT,
            width=32,
            height=28,
            command=self.abrir_menu_opcoes
        )
        self.btn_menu_opcoes.pack(side="right", padx=(0, 4))

        # Área de Histórico
        self.area_chat = ctk.CTkTextbox(
            self,
            font=("Consolas", 12),
            fg_color=COR_PAINEL,
            text_color=COR_TEXTO,
            corner_radius=12,
            border_width=1,
            border_color="#2E2E45",
            wrap="word"
        )
        self.area_chat.pack(fill="both", expand=True, padx=10, pady=5)

        self.area_chat._textbox.tag_config("voce", foreground=COR_VERDE_VOCE, font=("Consolas", 12, "bold"))
        self.area_chat._textbox.tag_config("outro", foreground=COR_ROXO_PRIVADO, font=("Consolas", 12, "bold"))
        self.area_chat._textbox.tag_config("sistema", foreground=COR_AMARELO_SISTEMA, font=("Consolas", 11, "italic"))
        self.area_chat._textbox.tag_config("link_arquivo", foreground=COR_AZUL_ACCENT, font=("Consolas", 12, "bold", "underline"))

        self.area_chat.configure(state="disabled")

        # Rodapé
        frame_rodape = ctk.CTkFrame(self, fg_color="transparent")
        frame_rodape.pack(fill="x", padx=10, pady=(5, 10))

        self.ent_mensagem = ctk.CTkEntry(
            frame_rodape,
            placeholder_text="Mensagem ou /ajuda, /clear...",
            font=("Segoe UI", 12),
            fg_color=COR_PAINEL,
            border_color="#2E2E45",
            corner_radius=20,
            height=40
        )
        self.ent_mensagem.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.ent_mensagem.bind("<Return>", lambda event: self.enviar_mensagem())

        btn_enviar = ctk.CTkButton(
            frame_rodape,
            text="Enviar",
            font=("Segoe UI", 11, "bold"),
            fg_color=COR_AZUL_ACCENT,
            hover_color=COR_HOVER_AZUL,
            corner_radius=20,
            width=80,
            height=40,
            command=self.enviar_mensagem
        )
        btn_enviar.pack(side="right")

        btn_anexo = ctk.CTkButton(
            frame_rodape,
            text="📎",
            font=("Segoe UI", 14),
            fg_color=COR_INPUT,
            hover_color=COR_HOVER_AZUL,
            corner_radius=20,
            width=40,
            height=40,
            command=lambda: self.app_principal.enviar_arquivo(destino=self.destinatario)
        )
        btn_anexo.pack(side="right", padx=(0, 8))

    def enviar_mensagem(self):
        texto = self.ent_mensagem.get().strip()
        if not texto:
            return

        cmd = texto.lower()

        if cmd == "/clear":
            self.area_chat.configure(state="normal")
            self.area_chat._textbox.delete("1.0", "end")
            self.area_chat.configure(state="disabled")
            self.ent_mensagem.delete(0, "end")
            return

        if cmd == "/ajuda":
            self.exibir_sistema(TEXTO_AJUDA)
            self.ent_mensagem.delete(0, "end")
            return

        if cmd.startswith("/apagar "):
            self.app_principal.enviar_comando_geral(texto)
            self.ent_mensagem.delete(0, "end")
            return

        self.app_principal.enviar_msg_privada(self.destinatario, texto)
        self.ent_mensagem.delete(0, "end")

    def abrir_menu_opcoes(self):
        menu = Menu(self, tearoff=0, bg=COR_PAINEL, fg=COR_TEXTO,
                    activebackground=COR_AZUL_ACCENT, activeforeground=COR_TEXTO, bd=0)
        menu.add_command(label="💡 Ajuda", command=self.executar_cmd_ajuda)
        menu.add_command(label="🧹 Limpar Tela", command=self.executar_cmd_clear)
        menu.add_command(label="🗑️ Apagar Mensagem por ID", command=self.executar_cmd_apagar)

        x = self.btn_menu_opcoes.winfo_rootx()
        y = self.btn_menu_opcoes.winfo_rooty() + self.btn_menu_opcoes.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def executar_cmd_ajuda(self):
        self.exibir_sistema(TEXTO_AJUDA)

    def executar_cmd_clear(self):
        self.area_chat.configure(state="normal")
        self.area_chat._textbox.delete("1.0", "end")
        self.area_chat.configure(state="disabled")

    def executar_cmd_apagar(self):
        id_str = simpledialog.askstring("Apagar Mensagem", "Digite o ID da mensagem que deseja apagar:", parent=self)
        if not id_str:
            return
        if id_str.strip().isdigit():
            self.app_principal.enviar_comando_geral(f"/apagar {id_str.strip()}")
        else:
            messagebox.showwarning("Aviso", "Digite um número de ID válido.")

    def exibir_mensagem(self, id_msg, hora, remetente, texto):
        self.area_chat.configure(state="normal")
        
        if remetente == self.app_principal.apelido:
            tag = "voce"
            nome_exibido = "Você"
        else:
            tag = "outro"
            nome_exibido = remetente

        tag_id_unica = f"msg_id_{id_msg}"
        self.area_chat._textbox.insert("end", f"[{hora}] [ID: {id_msg}] <{nome_exibido}>: {texto}\n", (tag, tag_id_unica))
        self.area_chat._textbox.see("end")
        self.area_chat.configure(state="disabled")

    def apagar_mensagem_por_id(self, id_msg, solicitante):
        tag_id_unica = f"msg_id_{id_msg}"
        self.area_chat.configure(state="normal")
        intervalos = self.area_chat._textbox.tag_ranges(tag_id_unica)
        if intervalos:
            inicio, fim = intervalos[0], intervalos[1]
            self.area_chat._textbox.delete(inicio, fim)
            self.area_chat._textbox.insert(inicio, f"🚫 [Mensagem ID {id_msg} apagada por '{solicitante}']\n", "sistema")
        self.area_chat.configure(state="disabled")

    def exibir_arquivo(self, id_msg, hora, remetente, nome_arquivo, caminho_local):
        self.area_chat.configure(state="normal")
        nome_exibido = "Você" if remetente == self.app_principal.apelido else remetente
        tag = "voce" if remetente == self.app_principal.apelido else "outro"

        if e_imagem(nome_arquivo):
            self.area_chat._textbox.insert("end", f"[{hora}] <{nome_exibido}>:\n", tag)

            if os.path.exists(caminho_local):
                try:
                    img_pil = Image.open(caminho_local)
                    img_pil.thumbnail((240, 160), Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img_pil)
                    self.referencias_imagens.append(tk_img)

                    pos_inicio = self.area_chat._textbox.index("end-1c")
                    self.area_chat._textbox.image_create("end", image=tk_img)
                    pos_fim = self.area_chat._textbox.index("end-1c")

                    tag_img = f"tag_img_{id_msg}"
                    self.area_chat._textbox.tag_add(tag_img, pos_inicio, pos_fim)
                    self.area_chat._textbox.tag_bind(
                        tag_img, "<Button-1>",
                        lambda e, c=caminho_local, r=nome_exibido, h=hora: self.app_principal.abrir_visualizador_imagem(c, r, h)
                    )
                    self.area_chat._textbox.tag_bind(tag_img, "<Enter>", lambda e: self.area_chat._textbox.config(cursor="hand2"))
                    self.area_chat._textbox.tag_bind(tag_img, "<Leave>", lambda e: self.area_chat._textbox.config(cursor=""))

                    self.area_chat._textbox.insert("end", "\n")
                except Exception:
                    pass
        else:
            tag_link = f"link_arquivo_{id_msg}"
            self.area_chat._textbox.insert("end", f"[{hora}] <{nome_exibido}> enviou um arquivo: ", tag)
            self.area_chat._textbox.insert("end", f"📎 {nome_arquivo}\n", ("link_arquivo", tag_link))

            self.area_chat._textbox.tag_bind(
                tag_link, "<Button-1>", 
                lambda e, c=caminho_local: abrir_no_sistema(c)
            )
            self.area_chat._textbox.tag_bind(tag_link, "<Enter>", lambda e: self.area_chat._textbox.config(cursor="hand2"))
            self.area_chat._textbox.tag_bind(tag_link, "<Leave>", lambda e: self.area_chat._textbox.config(cursor=""))

        self.area_chat._textbox.see("end")
        self.area_chat.configure(state="disabled")

    def exibir_sistema(self, texto):
        self.area_chat.configure(state="normal")
        self.area_chat._textbox.insert("end", texto + "\n", "sistema")
        self.area_chat._textbox.see("end")
        self.area_chat.configure(state="disabled")

    def fechar(self):
        if self.destinatario in self.app_principal.janelas_privadas:
            del self.app_principal.janelas_privadas[self.destinatario]
        self.destroy()


class ChatClienteGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.sock = None
        self.conectado = False
        self.apelido = ""
        
        self.janelas_privadas = {}
        self.referencias_imagens = []
        self.modal_imagem = None

        self.title("PyChat - Modern WhatsApp Style")
        self.geometry("850x650")
        self.configure(fg_color=COR_FUNDO_PRINCIPAL)
        
        self.protocol("WM_DELETE_WINDOW", self.fechar_conexao)
        self.criar_tela_login()

    def abrir_visualizador_imagem(self, caminho_imagem, remetente="", hora=""):
        """Garante a abertura de APENAS UM modal de imagem por vez."""
        if self.modal_imagem is not None:
            try:
                if self.modal_imagem.winfo_exists():
                    self.modal_imagem.destroy()
            except Exception:
                pass
        self.modal_imagem = ModalImagemDiscord(self, caminho_imagem, remetente, hora)

    def criar_tela_login(self):
        self.container_login = ctk.CTkFrame(self, fg_color="transparent", width=420, height=480)
        self.container_login.place(relx=0.5, rely=0.5, anchor="center")

        self.frame_login = ctk.CTkFrame(
            self.container_login, fg_color=COR_PAINEL, corner_radius=20, border_width=1, border_color="#2E2E45"
        )
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.9)

        ctk.CTkLabel(
            self.frame_login, text="⚡ PyChat Login", font=("Segoe UI", 22, "bold"), text_color=COR_AZUL_ACCENT
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
        entry = ctk.CTkEntry(frame, font=("Segoe UI", 12), fg_color=COR_INPUT, border_color="#2E2E45", corner_radius=10, height=36)
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

            threading.Thread(target=self.receber_mensagens, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao servidor:\n{e}")

    def criar_tela_chat(self):
        frame_topo = ctk.CTkFrame(self, fg_color=COR_PAINEL, corner_radius=15, height=50)
        frame_topo.pack(fill="x", padx=15, pady=(15, 0))
        
        ctk.CTkLabel(
            frame_topo, text=f"🟢 Conectado como: {self.apelido}", font=("Segoe UI", 13, "bold"), text_color=COR_VERDE_VOCE
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            frame_topo,
            text="📂 Abrir Pasta de Arquivos",
            font=("Segoe UI", 11, "bold"),
            fg_color="transparent",
            hover_color=COR_INPUT,
            text_color=COR_TEXTO,
            width=180,
            height=32,
            command=lambda: abrir_no_sistema(os.path.abspath(PASTA_ARQUIVOS_RECEBIDOS))
        ).pack(side="right", padx=(0, 20))

        self.btn_menu_opcoes = ctk.CTkButton(
            frame_topo,
            text="⋮",
            font=("Segoe UI", 18, "bold"),
            fg_color="transparent",
            hover_color=COR_INPUT,
            text_color=COR_TEXTO,
            width=36,
            height=32,
            command=self.abrir_menu_opcoes
        )
        self.btn_menu_opcoes.pack(side="right", padx=(0, 4))

        frame_corpo = ctk.CTkFrame(self, fg_color="transparent")
        frame_corpo.pack(fill="both", expand=True, padx=15, pady=12)

        self.area_chat = ctk.CTkTextbox(
            frame_corpo,
            font=("Consolas", 12),
            fg_color=COR_PAINEL,
            text_color=COR_TEXTO,
            corner_radius=15,
            border_width=1,
            border_color="#2E2E45",
            wrap="word"
        )
        self.area_chat.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.area_chat._textbox.tag_config("voce", foreground=COR_VERDE_VOCE, font=("Consolas", 12, "bold"))
        self.area_chat._textbox.tag_config("normal", foreground="#B9B4FA")
        self.area_chat._textbox.tag_config("sistema", foreground=COR_AMARELO_SISTEMA, font=("Consolas", 11, "italic"))
        self.area_chat._textbox.tag_config("link_arquivo", foreground=COR_AZUL_ACCENT, font=("Consolas", 12, "bold", "underline"))

        self.area_chat.configure(state="disabled")

        frame_sidebar = ctk.CTkFrame(frame_corpo, fg_color=COR_PAINEL, width=220, corner_radius=15, border_width=1, border_color="#2E2E45")
        frame_sidebar.pack(side="right", fill="y")
        frame_sidebar.pack_propagate(False)

        ctk.CTkLabel(frame_sidebar, text="ONLINE (Clique p/ Chat)", font=("Segoe UI", 11, "bold"), text_color="#80809D").pack(anchor="w", padx=15, pady=(15, 5))
        self.scroll_usuarios = ctk.CTkScrollableFrame(frame_sidebar, fg_color="transparent")
        self.scroll_usuarios.pack(fill="both", expand=True, padx=5, pady=5)

        frame_rodape = ctk.CTkFrame(self, fg_color="transparent", height=50)
        frame_rodape.pack(fill="x", padx=15, pady=(0, 15))

        self.ent_mensagem = ctk.CTkEntry(
            frame_rodape,
            placeholder_text="Mensagem pública ou /ajuda, /clear...",
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
            text="Enviar Geral",
            font=("Segoe UI", 12, "bold"),
            fg_color=COR_AZUL_ACCENT,
            hover_color=COR_HOVER_AZUL,
            corner_radius=25,
            width=110,
            height=46,
            command=self.enviar_mensagem
        )
        btn_enviar.pack(side="right")

        btn_anexo = ctk.CTkButton(
            frame_rodape,
            text="📎 Arquivo",
            font=("Segoe UI", 12, "bold"),
            fg_color=COR_INPUT,
            hover_color=COR_HOVER_AZUL,
            corner_radius=25,
            width=100,
            height=46,
            command=lambda: self.enviar_arquivo()
        )
        btn_anexo.pack(side="right", padx=(0, 8))

    def abrir_chat_privado(self, destinatario):
        if destinatario == self.apelido:
            return

        if destinatario in self.janelas_privadas:
            self.janelas_privadas[destinatario].focus()
        else:
            janela = JanelaChatPrivado(self, destinatario)
            self.janelas_privadas[destinatario] = janela

    def abrir_menu_opcoes(self):
        menu = Menu(self, tearoff=0, bg=COR_PAINEL, fg=COR_TEXTO,
                    activebackground=COR_AZUL_ACCENT, activeforeground=COR_TEXTO, bd=0)
        menu.add_command(label="💡 Ajuda", command=self.executar_cmd_ajuda)
        menu.add_command(label="🧹 Limpar Tela", command=self.executar_cmd_clear)
        menu.add_command(label="🗑️ Apagar Mensagem por ID", command=self.executar_cmd_apagar)
        menu.add_separator()
        menu.add_command(label="👥 Conversa Privada (clique no usuário)", command=self.executar_info_conversa_privada)

        x = self.btn_menu_opcoes.winfo_rootx()
        y = self.btn_menu_opcoes.winfo_rooty() + self.btn_menu_opcoes.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def executar_cmd_ajuda(self):
        self.adicionar_texto_chat(TEXTO_AJUDA, tag="sistema")

    def executar_cmd_clear(self):
        self.area_chat.configure(state="normal")
        self.area_chat._textbox.delete("1.0", "end")
        self.area_chat.configure(state="disabled")

    def executar_cmd_apagar(self):
        id_str = simpledialog.askstring("Apagar Mensagem", "Digite o ID da mensagem que deseja apagar:", parent=self)
        if not id_str:
            return
        if id_str.strip().isdigit():
            self.enviar_comando_geral(f"/apagar {id_str.strip()}")
        else:
            messagebox.showwarning("Aviso", "Digite um número de ID válido.")

    def executar_info_conversa_privada(self):
        messagebox.showinfo(
            "Conversa Privada",
            "Clique no nome de um usuário na lista à direita para abrir uma janela de conversa privada com ele."
        )

    def enviar_mensagem(self):
        texto = self.ent_mensagem.get().strip()
        if not texto or not self.conectado:
            return

        cmd = texto.lower()

        if cmd == "/clear":
            self.area_chat.configure(state="normal")
            self.area_chat._textbox.delete("1.0", "end")
            self.area_chat.configure(state="disabled")
            self.ent_mensagem.delete(0, "end")
            return

        if cmd == "/ajuda":
            self.adicionar_texto_chat(TEXTO_AJUDA, tag="sistema")
            self.ent_mensagem.delete(0, "end")
            return

        self.enviar_comando_geral(texto)
        self.ent_mensagem.delete(0, "end")

    def enviar_comando_geral(self, texto):
        if not self.conectado:
            return
        pacote = json.dumps({"tipo": "mensagem", "texto": texto}) + "\n"
        try:
            self.sock.sendall(pacote.encode("utf-8"))
        except Exception as e:
            self.adicionar_texto_chat(f"[ERRO]: Falha ao enviar pacote: {e}", tag="sistema")

    def enviar_arquivo(self, destino=None):
        if not self.conectado:
            return

        caminho = filedialog.askopenfilename(title="Selecione o arquivo para enviar")
        if not caminho:
            return

        try:
            tamanho_bytes = os.path.getsize(caminho)
            if tamanho_bytes > TAMANHO_MAXIMO_ARQUIVO_MB * 1024 * 1024:
                messagebox.showerror("Arquivo muito grande", f"O arquivo excede o limite de {TAMANHO_MAXIMO_ARQUIVO_MB}MB.")
                return

            with open(caminho, "rb") as f:
                conteudo_b64 = base64.b64encode(f.read()).decode("utf-8")

            nome_arquivo = os.path.basename(caminho)

            pacote = {
                "tipo": "arquivo",
                "nome_arquivo": nome_arquivo,
                "tamanho": tamanho_bytes,
                "conteudo": conteudo_b64
            }
            if destino:
                pacote["destino"] = destino

            self.sock.sendall((json.dumps(pacote) + "\n").encode("utf-8"))

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao enviar o arquivo:\n{e}")

    def enviar_msg_privada(self, destinatario, texto):
        if not self.conectado:
            return
        pacote = json.dumps({
            "tipo": "msg_privada",
            "destino": destinatario,
            "texto": texto
        }) + "\n"
        try:
            self.sock.sendall(pacote.encode("utf-8"))
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao enviar mensagem privada: {e}")

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
                        id_msg = pacote.get("id")
                        hora = pacote.get("hora", "")
                        remetente = pacote.get("remetente", "")
                        texto = pacote.get("texto", "")

                        msg_formatada = f"[{hora}] [ID: {id_msg}] <{remetente}>: {texto}"
                        tag_estilo = "voce" if remetente == self.apelido else "normal"
                        self.adicionar_mensagem_com_id(id_msg, msg_formatada, tag_estilo)

                    elif tipo == "msg_privada":
                        id_msg = pacote.get("id")
                        remetente = pacote.get("remetente")
                        destino = pacote.get("destino")
                        hora = pacote.get("hora")
                        texto = pacote.get("texto")

                        outro_usuario = destino if remetente == self.apelido else remetente

                        self.after(0, lambda u=outro_usuario, h=hora, r=remetente, t=texto, i=id_msg: 
                                   self.processar_msg_privada_recebida(u, h, r, t, i))

                    elif tipo == "apagar_msg":
                        id_msg = pacote.get("id")
                        solicitante = pacote.get("solicitante")
                        self.apagar_mensagem_por_id(id_msg, solicitante)

                    elif tipo == "arquivo":
                        id_msg = pacote.get("id")
                        remetente = pacote.get("remetente")
                        destino = pacote.get("destino")
                        hora = pacote.get("hora", "")
                        nome_arquivo = pacote.get("nome_arquivo", "arquivo")
                        conteudo_b64 = pacote.get("conteudo", "")

                        self.after(0, lambda i=id_msg, r=remetente, d=destino, h=hora, n=nome_arquivo, c=conteudo_b64:
                                   self.processar_arquivo_recebido(i, r, d, h, n, c))

                    elif tipo == "sistema":
                        self.adicionar_texto_chat(f"[SISTEMA]: {pacote.get('texto')}", tag="sistema")

                    elif tipo == "lista_usuarios":
                        usuarios = pacote.get("usuarios", [])
                        self.after(0, lambda u=usuarios: self.atualizar_lista_usuarios(u))

            except Exception as e:
                if self.conectado:
                    self.adicionar_texto_chat(f"[ERRO DE REDE]: {e}", tag="sistema")
                break

    def processar_arquivo_recebido(self, id_msg, remetente, destino, hora, nome_arquivo, conteudo_b64):
        try:
            os.makedirs(PASTA_ARQUIVOS_RECEBIDOS, exist_ok=True)
            caminho_salvo = os.path.join(PASTA_ARQUIVOS_RECEBIDOS, nome_arquivo)

            base, ext = os.path.splitext(caminho_salvo)
            contador = 1
            while os.path.exists(caminho_salvo):
                caminho_salvo = f"{base}_{contador}{ext}"
                contador += 1

            with open(caminho_salvo, "wb") as f:
                f.write(base64.b64decode(conteudo_b64))

            caminho_salvo = os.path.abspath(caminho_salvo)

        except Exception as e:
            self.adicionar_texto_chat(f"[ERRO]: Falha ao salvar arquivo recebido: {e}", tag="sistema")
            return

        if destino:
            outro_usuario = destino if remetente == self.apelido else remetente
            if outro_usuario not in self.janelas_privadas:
                self.abrir_chat_privado(outro_usuario)
            janela = self.janelas_privadas.get(outro_usuario)
            if janela:
                janela.exibir_arquivo(id_msg, hora, remetente, nome_arquivo, caminho_salvo)
        else:
            self.adicionar_arquivo_chat_geral(id_msg, hora, remetente, nome_arquivo, caminho_salvo)

    def adicionar_arquivo_chat_geral(self, id_msg, hora, remetente, nome_arquivo, caminho_salvo):
        def _inserir():
            nome_exibido = "Você" if remetente == self.apelido else remetente
            tag = "voce" if remetente == self.apelido else "normal"

            self.area_chat.configure(state="normal")

            if e_imagem(nome_arquivo):
                self.area_chat._textbox.insert("end", f"[{hora}] <{nome_exibido}>:\n", tag)

                if os.path.exists(caminho_salvo):
                    try:
                        img_pil = Image.open(caminho_salvo)
                        img_pil.thumbnail((240, 160), Image.Resampling.LANCZOS)
                        tk_img = ImageTk.PhotoImage(img_pil)
                        self.referencias_imagens.append(tk_img)

                        pos_inicio = self.area_chat._textbox.index("end-1c")
                        self.area_chat._textbox.image_create("end", image=tk_img)
                        pos_fim = self.area_chat._textbox.index("end-1c")

                        tag_img = f"tag_img_{id_msg}"
                        self.area_chat._textbox.tag_add(tag_img, pos_inicio, pos_fim)
                        self.area_chat._textbox.tag_bind(
                            tag_img, "<Button-1>",
                            lambda e, c=caminho_salvo, r=nome_exibido, h=hora: self.abrir_visualizador_imagem(c, r, h)
                        )
                        self.area_chat._textbox.tag_bind(tag_img, "<Enter>", lambda e: self.area_chat._textbox.config(cursor="hand2"))
                        self.area_chat._textbox.tag_bind(tag_img, "<Leave>", lambda e: self.area_chat._textbox.config(cursor=""))

                        self.area_chat._textbox.insert("end", "\n")
                    except Exception:
                        pass
            else:
                tag_link = f"link_arquivo_{id_msg}"
                self.area_chat._textbox.insert("end", f"[{hora}] <{nome_exibido}> enviou um arquivo: ", tag)
                self.area_chat._textbox.insert("end", f"📎 {nome_arquivo}\n", ("link_arquivo", tag_link))

                self.area_chat._textbox.tag_bind(
                    tag_link, "<Button-1>", 
                    lambda e, c=caminho_salvo: abrir_no_sistema(c)
                )
                self.area_chat._textbox.tag_bind(tag_link, "<Enter>", lambda e: self.area_chat._textbox.config(cursor="hand2"))
                self.area_chat._textbox.tag_bind(tag_link, "<Leave>", lambda e: self.area_chat._textbox.config(cursor=""))

            self.area_chat._textbox.see("end")
            self.area_chat.configure(state="disabled")

        self.after(0, _inserir)

    def processar_msg_privada_recebida(self, usuario_janela, hora, remetente, texto, id_msg):
        if usuario_janela not in self.janelas_privadas:
            self.abrir_chat_privado(usuario_janela)
        
        janela = self.janelas_privadas.get(usuario_janela)
        if janela:
            janela.exibir_mensagem(id_msg, hora, remetente, texto)

    def adicionar_mensagem_com_id(self, id_msg, texto, tag_estilo):
        def _inserir():
            self.area_chat.configure(state="normal")
            tag_id_unica = f"msg_id_{id_msg}"
            self.area_chat._textbox.insert("end", texto + "\n", (tag_estilo, tag_id_unica))
            self.area_chat._textbox.see("end")
            self.area_chat.configure(state="disabled")

        self.after(0, _inserir)

    def apagar_mensagem_por_id(self, id_msg, solicitante):
        def _apagar():
            tag_id_unica = f"msg_id_{id_msg}"

            self.area_chat.configure(state="normal")
            intervalos = self.area_chat._textbox.tag_ranges(tag_id_unica)
            if intervalos:
                inicio, fim = intervalos[0], intervalos[1]
                self.area_chat._textbox.delete(inicio, fim)
                self.area_chat._textbox.insert(inicio, f"🚫 [Mensagem ID {id_msg} apagada por '{solicitante}']\n", "sistema")
            self.area_chat.configure(state="disabled")

            for janela in list(self.janelas_privadas.values()):
                janela.apagar_mensagem_por_id(id_msg, solicitante)

        self.after(0, _apagar)

    def adicionar_texto_chat(self, texto, tag="normal"):
        def _inserir():
            self.area_chat.configure(state="normal")
            self.area_chat._textbox.insert("end", texto + "\n", tag)
            self.area_chat._textbox.see("end")
            self.area_chat.configure(state="disabled")

        self.after(0, _inserir)

    def atualizar_lista_usuarios(self, lista):
        for widget in self.scroll_usuarios.winfo_children():
            widget.destroy()

        for user in lista:
            e_voce = user == self.apelido
            
            if e_voce:
                lbl = ctk.CTkLabel(
                    self.scroll_usuarios,
                    text=f"• {user} (Você)",
                    text_color=COR_VERDE_VOCE,
                    font=("Segoe UI", 12, "bold")
                )
                lbl.pack(anchor="w", pady=3, padx=5)
            else:
                btn_user = ctk.CTkButton(
                    self.scroll_usuarios,
                    text=f"💬 {user}",
                    font=("Segoe UI", 12),
                    fg_color="transparent",
                    hover_color=COR_INPUT,
                    text_color=COR_TEXTO,
                    anchor="w",
                    height=32,
                    command=lambda u=user: self.abrir_chat_privado(u)
                )
                btn_user.pack(fill="x", pady=2)

    def fechar_conexao(self):
        if self.conectado and self.sock:
            self.conectado = False
            try:
                self.sock.close()
            except Exception:
                pass
        self.destroy()


if __name__ == "__main__":
    app = ChatClienteGUI()
    app.mainloop()