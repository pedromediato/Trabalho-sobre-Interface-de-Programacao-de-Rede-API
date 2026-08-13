"""
servidor.py - Servidor Bate-Papo Multi-thread com Protocolo JSON

Referências utilizadas:
- https://docs.python.org/pt-br/3/howto/sockets.html
- https://docs.python.org/3/library/socket.html
- https://docs.python.org/3/library/threading.html
- https://docs.python.org/3/library/json.html
- https://docs.python.org/3/library/datetime.html

Funcionalidades deste código:
1) Comunicação estruturada via JSON (módulo 'json' nativo do Python).
2) Envio delimitado por quebra de linha ('\n') para resolver o problema de colisão de pacotes TCP.
3) Broadcast automático da lista de usuários online sempre que alguém entra ou sai.
4) Bot de comandos para clientes e servidor (/ajuda, /usuarios, /hora).
5) Comando exclusivo do servidor (/log) para exportar histórico sob demanda com nome timestamped.
6) Suporte a mensagens privadas (/msg <apelido> <mensagem>).
"""

import socket
import threading
import json
from datetime import datetime  # Para manipular datas e horários dos eventos

# --- Configurações da Rede ---
# Usa IP local (127.0.0.1) e uma porta alta (8080) fora da faixa reservada (0-1024).
HOST = "127.0.0.1"
PORTA = 8080
TAMANHO_BUFFER = 2048  # Aumentado para suportar pacotes JSON maiores

# --- Gerenciamento da Lista de Clientes Conectados ---
# Armazena dicionários no formato: {"socket": socket_obj, "apelido": "Nome"}
clientes = []
trava_clientes = threading.Lock()  # Lock para evitar que duas threads alterem a lista juntas

# --- Gerenciamento de Histórico de Log em Memória ---
# As conversas ficam salvas na RAM e só vão para disco quando o servidor digita /log
historico_em_memoria = []
trava_historico = threading.Lock()  # Lock para acesso thread-safe ao histórico


def registrar_evento(texto):
    """
    Armazena qualquer mensagem ou evento na lista em memória,
    acrescentando a data e hora formatadas [DD/MM/AAAA HH:MM:SS].
    """
    data_hora = datetime.now().strftime("[%d/%m/%Y %H:%M:%S]")
    linha = f"{data_hora} {texto}"
    with trava_historico:
        historico_em_memoria.append(linha)


def gerar_arquivo_log():
    """
    Comando EXCLUSIVO do Servidor (/log):
    Cria um arquivo físico .txt contendo todo o histórico acumulado na memória.
    O nome do arquivo inclui o dia, mês, ano, hora, minuto e segundo da solicitação.
    Exemplo: log_13-08-2026_14-30-00.txt
    """
    agora = datetime.now()
    nome_arquivo = agora.strftime("log_%d-%m-%Y_%H-%M-%S.txt")

    # Copia o conteúdo da memória em uma operação segura
    with trava_historico:
        conteudo = "\n".join(historico_em_memoria)

    try:
        # Modo "w" (write): cria um novo arquivo limpo com o nome gerado
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo + ("\n" if conteudo else ""))
        print(f"\n[SERVIDOR] Log do chat gerado com sucesso! Arquivo: '{nome_arquivo}'\n")
    except Exception as e:
        print(f"\n[ERRO LOG] Não foi possível gerar o arquivo de log: {e}\n")


def enviar_json(sock, dados_dict):
    """
    Converte um dicionário Python em uma string JSON, adiciona um caractere
    de quebra de linha ('\n') no final e envia como bytes pelo socket.
    O '\n' serve como delimitador de mensagem no lado do receptor.
    """
    try:
        payload = json.dumps(dados_dict) + "\n"
        sock.sendall(payload.encode("utf-8"))
    except:
        pass  # Se falhar o envio (cliente desconectado), o tratamento é feito no loop principal


def retransmitir_pacote(dados_dict, remetente_socket=None):
    """
    Transmite um pacote JSON para todos os clientes conectados.
    Se 'remetente_socket' for informado, não reenvia para quem originou a mensagem.
    """
    with trava_clientes:
        for cliente in clientes:
            if cliente["socket"] != remetente_socket:
                enviar_json(cliente["socket"], dados_dict)


def enviar_lista_usuarios_atualizada():
    """
    Notifica TODOS os clientes conectados enviando a lista atualizada de apelidos.
    Crucial para atualizar a barra lateral de usuários na futura Interface Gráfica!
    """
    with trava_clientes:
        lista_apelidos = [c["apelido"] for c in clientes]
        for cliente in clientes:
            enviar_json(cliente["socket"], {
                "tipo": "lista_usuarios",
                "usuarios": lista_apelidos
            })


def enviar_mensagens_servidor():
    """
    Thread dedicada para capturar o teclado do operador do SERVIDOR.
    Permite rodar comandos (/ajuda, /usuarios, /hora, /log) ou mandar avisos globais.
    """
    while True:
        try:
            mensagem = input()
            if not mensagem.strip():
                continue

            # Tratamento de comandos do operador do servidor
            if mensagem.startswith("/"):
                comando_minusculo = mensagem.lower().strip()

                if comando_minusculo == "/ajuda":
                    print(
                        "\n--- COMANDOS DO OPERADOR DO SERVIDOR ---\n"
                        "/ajuda      -> Mostra este menu de ajuda no servidor\n"
                        "/usuarios   -> Lista os usuários conectados no momento\n"
                        "/hora       -> Exibe a hora exata do servidor\n"
                        "/log        -> EXCLUSIVO: Gera o arquivo .txt com o histórico do chat\n"
                        "-----------------------------------------\n"
                    )

                elif comando_minusculo in ["/usuarios", "/online"]:
                    with trava_clientes:
                        lista_apelidos = [c["apelido"] for c in clientes]
                    print(f"[BOT/SERVIDOR]: Usuários online ({len(lista_apelidos)}): {', '.join(lista_apelidos)}")

                elif comando_minusculo == "/hora":
                    hora_atual = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
                    print(f"[BOT/SERVIDOR]: Data e hora no servidor: {hora_atual}")

                elif comando_minusculo == "/log":
                    gerar_arquivo_log()

                else:
                    print(f"[BOT/SERVIDOR]: Comando '{mensagem}' não reconhecido. Digite /ajuda para ver as opções.")

                continue

            # Caso não seja comando, transmite mensagem global como [SERVIDOR]
            pacote = {
                "tipo": "mensagem",
                "remetente": "SERVIDOR",
                "texto": mensagem,
                "hora": datetime.now().strftime("%H:%M")
            }
            print(f"[SERVIDOR]: {mensagem}")
            registrar_evento(f"[SERVIDOR]: {mensagem}")
            retransmitir_pacote(pacote)

        except:
            break


def tratar_cliente(socket_cliente, endereco_cliente):
    """
    Thread dedicada para gerenciar a conexão individual de um cliente específico.
    """
    apelido = "Desconhecido"
    buffer_dados = ""  # Buffer para acumular fragmentos de pacotes recebidos do TCP

    try:
        # --- 1) APERTO DE MÃO (Handshake) ---
        # A primeira mensagem enviada pelo cliente deve ser o JSON de conexão contendo o Apelido.
        dados_iniciais = socket_cliente.recv(TAMANHO_BUFFER).decode("utf-8")
        if not dados_iniciais:
            socket_cliente.close()
            return

        pacote_conexao = json.loads(dados_iniciais.strip())
        apelido = pacote_conexao.get("apelido", "Desconhecido")

        # Adiciona o cliente na lista global do servidor
        with trava_clientes:
            clientes.append({"socket": socket_cliente, "apelido": apelido})

        msg_conexao = f"[SERVIDOR] Cliente conectado: {endereco_cliente} (Apelido: {apelido})"
        print(msg_conexao)
        registrar_evento(f"EVENTO: {apelido} conectou-se a partir de {endereco_cliente}")

        # Anuncia para os outros usuários que alguém entrou
        retransmitir_pacote({
            "tipo": "sistema",
            "texto": f"{apelido} entrou no bate-papo!"
        }, remetente_socket=socket_cliente)

        # Transmite a lista de usuários online atualizada para todos
        enviar_lista_usuarios_atualizada()

        # --- 2) LAÇO PRINCIPAL DE MENSAGENS ---
        while True:
            dados_brutos = socket_cliente.recv(TAMANHO_BUFFER).decode("utf-8")
            
            # Quando recv() retorna vazio, significa que o cliente fechou a conexão
            if not dados_brutos:
                break

            # Acumula no buffer local da thread para processar mensagem por mensagem (delimitada por \n)
            buffer_dados += dados_brutos
            
            while "\n" in buffer_dados:
                linha_json, buffer_dados = buffer_dados.split("\n", 1)
                if not linha_json.strip():
                    continue

                # Converte a string JSON recebida de volta para Dicionário Python
                pacote = json.loads(linha_json)
                tipo_msg = pacote.get("tipo")

                if tipo_msg == "mensagem":
                    texto = pacote.get("texto", "").strip()

                    # --- VERIFICAÇÃO DE COMANDOS DO CLIENTE ---
                    if texto.startswith("/"):
                        comando_minusculo = texto.lower()

                        if comando_minusculo == "/ajuda":
                            res = (
                                "\n--- COMANDOS DO BATE-PAPO ---\n"
                                "/ajuda                 -> Mostra este menu de ajuda\n"
                                "/usuarios              -> Lista os usuários conectados no momento\n"
                                "/hora                  -> Exibe a hora exata do servidor\n"
                                "/msg <apelido> <texto> -> Envia uma mensagem privada\n"
                                "------------------------------------\n"
                            )
                            enviar_json(socket_cliente, {"tipo": "sistema", "texto": res})

                        elif comando_minusculo in ["/usuarios", "/online"]:
                            with trava_clientes:
                                lista_apelidos = [c["apelido"] for c in clientes]
                            res = f"Usuários online ({len(lista_apelidos)}): {', '.join(lista_apelidos)}"
                            enviar_json(socket_cliente, {"tipo": "sistema", "texto": res})

                        elif comando_minusculo == "/hora":
                            hora_atual = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
                            enviar_json(socket_cliente, {"tipo": "sistema", "texto": f"Data e hora no servidor: {hora_atual}"})

                        # --- TRATAMENTO DE MENSAGEM PRIVADA (/msg) ---
                        elif comando_minusculo.startswith("/msg "):
                            partes = texto.split(" ", 2)
                            if len(partes) < 3:
                                enviar_json(socket_cliente, {"tipo": "sistema", "texto": "Uso correto: /msg <apelido> <mensagem>"})
                            else:
                                destinatario_apelido = partes[1].strip()
                                mensagem_privada = partes[2].strip()

                                # Busca o socket do destinatário
                                socket_destinatario = None
                                with trava_clientes:
                                    for c in clientes:
                                        if c["apelido"].lower() == destinatario_apelido.lower():
                                            socket_destinatario = c["socket"]
                                            break

                                if socket_destinatario:
                                    hora_formatada = datetime.now().strftime("%H:%M")
                                    
                                    # Envia a mensagem privada apenas para o destinatário
                                    enviar_json(socket_destinatario, {
                                        "tipo": "msg_privada",
                                        "remetente": apelido,
                                        "texto": mensagem_privada,
                                        "hora": hora_formatada
                                    })
                                    # Envia a confirmação para o remetente
                                    enviar_json(socket_cliente, {
                                        "tipo": "sistema",
                                        "texto": f"[Privada para {destinatario_apelido}]: {mensagem_privada}"
                                    })
                                    
                                    print(f"[LOG de mensagens privadas] {apelido} -> {destinatario_apelido}: {mensagem_privada}")
                                    registrar_evento(f"[LOG de mensagens privadas] {apelido} -> {destinatario_apelido}: {mensagem_privada}")
                                else:
                                    enviar_json(socket_cliente, {"tipo": "sistema", "texto": f"Usuário '{destinatario_apelido}' não encontrado."})

                        else:
                            enviar_json(socket_cliente, {"tipo": "sistema", "texto": f"Comando '{texto}' não reconhecido."})

                        # Pula a retransmissão pública pois foi um comando
                        continue

                    # Se o usuário digitou "sair", encerra o laço
                    if texto.lower() == "sair":
                        break

                    # Retransmissão de MENSAGEM PÚBLICA NORMAL para todos os outros clientes
                    hora_formatada = datetime.now().strftime("%H:%M")
                    pacote_saida = {
                        "tipo": "mensagem",
                        "remetente": apelido,
                        "texto": texto,
                        "hora": hora_formatada
                    }
                    print(f"[{apelido}]: {texto}")
                    registrar_evento(f"[{apelido}]: {texto}")
                    retransmitir_pacote(pacote_saida, remetente_socket=socket_cliente)

    except Exception as e:
        print(f"[SERVIDOR] Erro na conexão com {apelido}: {e}")

    finally:
        # --- LIMPEZA AO DESCONECTAR ---
        # Remove o cliente da lista global
        with trava_clientes:
            for c in clientes:
                if c["socket"] == socket_cliente:
                    clientes.remove(c)
                    break

        socket_cliente.close()  # Fecha o socket explicitamente
        print(f"[SERVIDOR] Cliente {apelido} desconectou.")
        registrar_evento(f"EVENTO: {apelido} desconectou-se.")

        # Notifica os outros clientes e envia a lista de usuários online atualizada
        retransmitir_pacote({"tipo": "sistema", "texto": f"{apelido} saiu do bate-papo."})
        enviar_lista_usuarios_atualizada()


def iniciar_servidor():
    """
    Função principal que inicializa o socket servidor TCP IPv4 e aguarda conexões.
    """
    socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket_servidor.bind((HOST, PORTA))
    socket_servidor.listen(5)

    print(f"[SERVIDOR] Aguardando conexões em {HOST}:{PORTA}...\n")
    registrar_evento("--- SERVIDOR INICIADO ---")

    # Inicia a thread que escuta a digitação do operador no terminal do servidor
    thread_envio = threading.Thread(target=enviar_mensagens_servidor, daemon=True)
    thread_envio.start()

    # Laço principal para aceitar múltiplos clientes simultâneos
    while True:
        try:
            socket_cliente, endereco_cliente = socket_servidor.accept()
            # Para cada cliente que conecta, cria uma Thread independente
            thread_cliente = threading.Thread(
                target=tratar_cliente,
                args=(socket_cliente, endereco_cliente),
                daemon=True
            )
            thread_cliente.start()
        except KeyboardInterrupt:
            print("\n[SERVIDOR] Encerramento solicitado via teclado.")
            registrar_evento("--- SERVIDOR ENCERRADO PELO OPERADOR ---")
            break

    socket_servidor.close()


if __name__ == "__main__":
    iniciar_servidor()