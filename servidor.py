import socket
import threading
import json
from datetime import datetime
import os

HOST = "127.0.0.1"
PORTA = 8080

clientes = []                   
historico_mensagens_id = {}     

lock_clientes = threading.Lock()
lock_historico = threading.Lock()
lock_id = threading.Lock()

contador_id_msg = 0

TEXTO_AJUDA_SISTEMA = (
    "\n--- GUIA DE COMANDOS DO CHAT ---\n"
    "• /ajuda             -> Exibe esta lista de ajuda\n"
    "• /clear             -> Limpa a tela desta janela\n"
    "• /apagar <id>       -> Apaga sua mensagem pelo ID (ex: /apagar 3)\n"
    "• Clique no Usuário  -> Abre janela de conversa privada\n"
    "-----------------------------------"
)


def gerar_novo_id():
    global contador_id_msg
    with lock_id:
        contador_id_msg += 1
        return contador_id_msg


def registrar_evento(mensagem):
    data_hora = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    linha = f"{data_hora} {mensagem}"
    print(linha)
    try:
        with open("servidor_log.txt", "a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except Exception:
        pass


def enviar_json(socket_destino, pacote_dicionario):
    try:
        texto_json = json.dumps(pacote_dicionario) + "\n"
        socket_destino.sendall(texto_json.encode("utf-8"))
    except Exception:
        pass


def retransmitir_pacote(pacote_dicionario, socket_remetente=None):
    with lock_clientes:
        for c in clientes:
            if socket_remetente is None or c["socket"] != socket_remetente:
                enviar_json(c["socket"], pacote_dicionario)


def enviar_lista_usuarios_atualizada():
    with lock_clientes:
        nomes_online = [c["apelido"] for c in clientes]
        lista_detalhada = [{"apelido": c["apelido"], "status": c.get("status", "Online")} for c in clientes]
    
    pacote = {
        "tipo": "lista_usuarios",
        "usuarios": nomes_online,
        "usuarios_detalhado": lista_detalhada
    }
    retransmitir_pacote(pacote)


def processar_remocao_mensagem(id_msg, solicitante="SERVIDOR"):
    with lock_historico:
        msg_info = historico_mensagens_id.get(id_msg)
        
        if not msg_info:
            return False, "Mensagem não encontrada ou já foi apagada."
            
        if solicitante != "SERVIDOR" and msg_info["remetente"] != solicitante:
            return False, "Você só pode apagar as suas próprias mensagens!"
            
        del historico_mensagens_id[id_msg]

    pacote_apagar = {
        "tipo": "apagar_msg",
        "id": id_msg,
        "solicitante": solicitante
    }
    retransmitir_pacote(pacote_apagar)
    registrar_evento(f"[APAGADA] Mensagem ID {id_msg} foi removida por '{solicitante}'.")
    return True, "Mensagem apagada com sucesso."


def enviar_mensagens_servidor():
    while True:
        try:
            comando = input()
            if not comando.strip():
                continue
                
            cmd_lower = comando.lower()

            if cmd_lower == "/clear":
                os.system('cls' if os.name == 'nt' else 'clear')
                print("[SERVIDOR] Tela do terminal limpa com sucesso.")
                
            elif cmd_lower == "/ajuda":
                print("\n--- COMANDOS DO TERMINAL DO SERVIDOR ---")
                print("/ajuda       -> Exibe este menu de ajuda")
                print("/clear       -> Limpa o terminal do servidor")
                print("/apagar <id> -> Apaga qualquer mensagem pelo ID")
                print("<mensagem>   -> Envia aviso do sistema para todos")
                print("-------------------------------------------\n")

            elif comando.startswith("/apagar "):
                partes = comando.split()
                if len(partes) >= 2 and partes[1].isdigit():
                    id_para_apagar = int(partes[1])
                    sucesso, retorno = processar_remocao_mensagem(id_para_apagar, solicitante="SERVIDOR")
                    print(f"[SERVIDOR] {retorno}")
                else:
                    print("[ERRO] Use o formato: /apagar <numero_do_id>")
                    
            else:
                pacote_sistema = {
                    "tipo": "sistema",
                    "texto": f"[AVISO DO SERVIDOR]: {comando}"
                }
                retransmitir_pacote(pacote_sistema)
                
        except Exception as e:
            print(f"[ERRO NO TERMINAL DO SERVIDOR]: {e}")


def tratar_cliente(socket_cliente, endereco_cliente):
    apelido = "Desconhecido"
    buffer_dados = ""

    try:
        dados_brutos = socket_cliente.recv(2048).decode("utf-8")
        if "\n" in dados_brutos:
            primeira_linha = dados_brutos.split("\n")[0]
            pacote_login = json.loads(primeira_linha)
            apelido = pacote_login.get("apelido", f"User_{endereco_cliente[1]}").strip()
            status_inicial = pacote_login.get("status", "Online")

        with lock_clientes:
            clientes.append({
                "socket": socket_cliente, 
                "apelido": apelido,
                "status": status_inicial
            })

        registrar_evento(f"[CONEXÃO] '{apelido}' entrou vindo do endereço {endereco_cliente}.")
        
        enviar_json(socket_cliente, {"tipo": "sistema", "texto": f"Bem-vindo ao bate-papo, {apelido}! Digite /ajuda para ver os comandos."})
        retransmitir_pacote({"tipo": "sistema", "texto": f"'{apelido}' entrou na sala."})
        enviar_lista_usuarios_atualizada()

        while True:
            dados = socket_cliente.recv(2048).decode("utf-8")
            if not dados:
                break

            buffer_dados += dados

            while "\n" in buffer_dados:
                linha, buffer_dados = buffer_dados.split("\n", 1)
                if not linha.strip():
                    continue

                pacote = json.loads(linha)
                tipo = pacote.get("tipo")

                if tipo == "status":
                    novo_status = pacote.get("status", "Online")
                    with lock_clientes:
                        for c in clientes:
                            if c["socket"] == socket_cliente:
                                c["status"] = novo_status
                                break

                    pacote_status = {
                        "tipo": "status",
                        "remetente": apelido,
                        "status": novo_status
                    }
                    retransmitir_pacote(pacote_status)
                    enviar_lista_usuarios_atualizada()
                    registrar_evento(f"[STATUS] '{apelido}' alterou seu status para '{novo_status}'.")

                elif tipo == "typing":
                    destino = pacote.get("destino")
                    pacote_typing = {
                        "tipo": "typing",
                        "remetente": apelido,
                        "destino": destino
                    }
                    if destino:
                        with lock_clientes:
                            for c in clientes:
                                if c["apelido"].lower() == destino.lower():
                                    enviar_json(c["socket"], pacote_typing)
                                    break
                    else:
                        retransmitir_pacote(pacote_typing, socket_remetente=socket_cliente)

                elif tipo == "mensagem":
                    texto = pacote.get("texto", "").strip()

                    if texto.lower() == "/ajuda":
                        enviar_json(socket_cliente, {"tipo": "sistema", "texto": TEXTO_AJUDA_SISTEMA})

                    elif texto.startswith("/apagar "):
                        partes = texto.split()
                        if len(partes) >= 2 and partes[1].isdigit():
                            id_alvo = int(partes[1])
                            sucesso, resposta = processar_remocao_mensagem(id_alvo, solicitante=apelido)
                            if not sucesso:
                                enviar_json(socket_cliente, {"tipo": "sistema", "texto": f"❌ {resposta}"})
                        else:
                            enviar_json(socket_cliente, {"tipo": "sistema", "texto": "Uso correto: /apagar <numero_id>"})

                    else:
                        novo_id = gerar_novo_id()
                        hora_atual = datetime.now().strftime("%H:%M")

                        with lock_historico:
                            historico_mensagens_id[novo_id] = {"remetente": apelido, "texto": texto}

                        pacote_difusao = {
                            "tipo": "mensagem",
                            "id": novo_id,
                            "hora": hora_atual,
                            "remetente": apelido,
                            "texto": texto
                        }
                        retransmitir_pacote(pacote_difusao)

                elif tipo == "msg_privada":
                    destino = pacote.get("destino", "").strip()
                    texto = pacote.get("texto", "").strip()
                    hora_atual = datetime.now().strftime("%H:%M")

                    if not texto or not destino:
                        continue

                    if texto.lower() == "/ajuda":
                        enviar_json(socket_cliente, {"tipo": "sistema", "texto": TEXTO_AJUDA_SISTEMA})
                        continue

                    novo_id = gerar_novo_id()

                    with lock_historico:
                        historico_mensagens_id[novo_id] = {
                            "remetente": apelido,
                            "destino": destino,
                            "texto": texto
                        }

                    socket_destino = None
                    socket_remetente = socket_cliente

                    with lock_clientes:
                        for c in clientes:
                            if c["apelido"].lower() == destino.lower():
                                socket_destino = c["socket"]
                                break

                    pacote_privado = {
                        "tipo": "msg_privada",
                        "id": novo_id,
                        "remetente": apelido,
                        "destino": destino,
                        "hora": hora_atual,
                        "texto": texto
                    }

                    if socket_destino:
                        enviar_json(socket_destino, pacote_privado)
                        if socket_destino != socket_remetente:
                            enviar_json(socket_remetente, pacote_privado)
                        registrar_evento(f"[PRIVADO ID {novo_id}] De '{apelido}' para '{destino}'")
                    else:
                        enviar_json(socket_cliente, {
                            "tipo": "sistema",
                            "texto": f"❌ O usuário '{destino}' não está online."
                        })

                elif tipo == "arquivo":
                    nome_arquivo = pacote.get("nome_arquivo", "arquivo_desconhecido")
                    conteudo_b64 = pacote.get("conteudo", "")
                    tamanho = pacote.get("tamanho", 0)
                    destino = pacote.get("destino", "").strip()
                    hora_atual = datetime.now().strftime("%H:%M")

                    if not conteudo_b64:
                        continue

                    novo_id = gerar_novo_id()

                    with lock_historico:
                        historico_mensagens_id[novo_id] = {
                            "remetente": apelido,
                            "destino": destino if destino else None,
                            "texto": f"[arquivo] {nome_arquivo}"
                        }

                    pacote_arquivo = {
                        "tipo": "arquivo",
                        "id": novo_id,
                        "remetente": apelido,
                        "nome_arquivo": nome_arquivo,
                        "tamanho": tamanho,
                        "conteudo": conteudo_b64,
                        "hora": hora_atual
                    }

                    if destino:
                        pacote_arquivo["destino"] = destino
                        socket_destino_arquivo = None
                        with lock_clientes:
                            for c in clientes:
                                if c["apelido"].lower() == destino.lower():
                                    socket_destino_arquivo = c["socket"]
                                    break

                        if socket_destino_arquivo:
                            enviar_json(socket_destino_arquivo, pacote_arquivo)
                            if socket_destino_arquivo != socket_cliente:
                                enviar_json(socket_cliente, pacote_arquivo)
                            registrar_evento(f"[ARQUIVO PRIVADO ID {novo_id}] '{apelido}' enviou '{nome_arquivo}' para '{destino}'.")
                        else:
                            enviar_json(socket_cliente, {
                                "tipo": "sistema",
                                "texto": f"❌ O usuário '{destino}' não está online."
                            })
                    else:
                        retransmitir_pacote(pacote_arquivo)
                        registrar_evento(f"[ARQUIVO ID {novo_id}] '{apelido}' enviou o arquivo '{nome_arquivo}' para a sala.")

    except Exception:
        pass

    finally:
        with lock_clientes:
            clientes[:] = [c for c in clientes if c["socket"] != socket_cliente]

        socket_cliente.close()
        registrar_evento(f"[DESCONEXÃO] '{apelido}' saiu da sala.")
        retransmitir_pacote({"tipo": "sistema", "texto": f"'{apelido}' saiu da sala."})
        enviar_lista_usuarios_atualizada()


def iniciar_servidor():
    socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        socket_servidor.bind((HOST, PORTA))
        socket_servidor.listen()
        print(f"=== SERVIDOR ATIVO EM {HOST}:{PORTA} ===")
        registrar_evento("--- SERVIDOR INICIADO ---")

        threading.Thread(target=enviar_mensagens_servidor, daemon=True).start()

        while True:
            sock_cliente, end_cliente = socket_servidor.accept()
            threading.Thread(target=tratar_cliente, args=(sock_cliente, end_cliente), daemon=True).start()

    except KeyboardInterrupt:
        print("\n[SERVIDOR] Encerrado pelo teclado (Ctrl+C).")
    finally:
        socket_servidor.close()

if __name__ == "__main__":
    iniciar_servidor()