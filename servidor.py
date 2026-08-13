"""
servidor.py

Base do SERVIDOR do trabalho de Sockets (Semana 1).
Referências utilizadas:
- https://docs.python.org/pt-br/3/howto/sockets.html
- https://docs.python.org/3/library/socket.html
- https://docs.python.org/3/library/threading.html
- https://docs.python.org/3/library/datetime.html

Nesta etapa, o código foi expandido para incluir:
1) Bot de Comandos para Clientes e Servidor (/ajuda, /usuarios, /hora)
2) Comando EXCLUSIVO do Servidor (/log) para gerar histórico em .txt sob demanda
3) Mensagens Privadas entre usuários (/msg <apelido> <mensagem>)
"""

import socket
import threading
from datetime import datetime  # Usado para obter a hora e data atual do servidor

# --- Configurações básicas ---
# Segundo o HOWTO do Python, portas baixas (abaixo de 1024) costumam ser
# reservadas para serviços conhecidos (HTTP, FTP, etc). Por isso usamos
# uma porta alta, "de brincadeira", como 8080.
HOST = "127.0.0.1"  # localhost -> só aceita conexões da própria máquina
PORTA = 8080
TAMANHO_BUFFER = 1024  # quantidade de bytes lidos por vez no recv()

# --- Gerenciamento de múltiplos clientes ---
# Lista global para armazenar os clientes conectados.
# Cada elemento é um dicionário contendo o socket e o apelido de quem conectou.
clientes = []
trava_clientes = threading.Lock()  # Garante acesso seguro à lista em ambiente multi-thread

# --- Gerenciamento do Histórico de Log em Memória ---
# [MODIFICAÇÃO DO GRUPO] O log deixa de ser salvo automaticamente em disco
# e passa a ser acumulado em memória para ser exportado sob demanda via /log.
historico_em_memoria = []
trava_historico = threading.Lock()  # Garante acesso seguro ao histórico em ambiente multi-thread


def registrar_evento(texto):
    """
    [MODIFICAÇÃO DO GRUPO]
    Armazena mensagens e eventos na memória junto com a data e hora exatas.
    """
    data_hora = datetime.now().strftime("[%d/%m/%Y %H:%M:%S]")
    linha = f"{data_hora} {texto}"
    with trava_historico:
        historico_em_memoria.append(linha)


def gerar_arquivo_log():
    """
    [MODIFICAÇÃO DO GRUPO]
    Gera um arquivo .txt sob demanda contendo o histórico das conversas.
    O nome do arquivo é gerado dinamicamente com a data e hora da solicitação.
    Exemplo: log_13-08-2026_11-54-25.txt
    """
    agora = datetime.now()
    nome_arquivo = agora.strftime("historico_chat_%d-%m-%Y_%H-%M-%S.txt")

    with trava_historico:
        conteudo = "\n".join(historico_em_memoria)

    try:
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo + ("\n" if conteudo else ""))
        print(f"\n[SERVIDOR] Log do chat gerado com sucesso! Arquivo: '{nome_arquivo}'\n")
    except Exception as e:
        print(f"\n[ERRO LOG] Não foi possível gerar o arquivo de log: {e}\n")


def retransmitir_mensagem(mensagem_bytes, remetente_socket=None):
    """
    Retransmite os bytes recebidos para todos os outros clientes conectados no servidor.
    Se remetente_socket for None, envia a mensagem para TODOS os clientes.
    """
    with trava_clientes:
        for cliente in clientes:
            # Não reenvia a mensagem de volta para o próprio cliente que a enviou
            if cliente["socket"] != remetente_socket:
                try:
                    # sendall() garante que todos os bytes sejam enviados,
                    # tratando internamente o que o HOWTO chama de "não enviar tudo de uma vez"
                    cliente["socket"].sendall(mensagem_bytes)
                except:
                    # Se falhar o envio, a limpeza da conexão é tratada na thread do cliente
                    pass


def enviar_mensagens_servidor():
    """
    Thread dedicada exclusivamente para permitir que o operador do servidor
    digite comandos (/ajuda, /usuarios, /hora, /log) ou envie mensagens de broadcast.
    """
    while True:
        try:
            mensagem = input()
            if not mensagem.strip():
                continue

            # =========================================================
            # [MODIFICAÇÃO DO GRUPO] COMANDOS EXECUTADOS PELO SERVIDOR
            # =========================================================
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
                    total = len(lista_apelidos)
                    print(f"[BOT/SERVIDOR]: Usuários online ({total}): {', '.join(lista_apelidos)}")

                elif comando_minusculo == "/hora":
                    hora_atual = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
                    print(f"[BOT/SERVIDOR]: Data e hora no servidor: {hora_atual}")

                elif comando_minusculo == "/log":
                    gerar_arquivo_log()

                else:
                    print(f"[BOT/SERVIDOR]: Comando '{mensagem}' não reconhecido. Digite /ajuda para ver as opções.")

                continue

            # Se não for comando, envia mensagem pública como [SERVIDOR]
            msg_formatada = f"[SERVIDOR]: {mensagem}\n"
            print(f"[SERVIDOR]: {mensagem}")
            registrar_evento(f"[SERVIDOR]: {mensagem}")

            # Transmite para TODOS os clientes conectados (remetente_socket=None)
            retransmitir_mensagem(msg_formatada.encode("utf-8"), remetente_socket=None)

        except:
            break


def tratar_cliente(socket_cliente, endereco_cliente):
    """
    Esta função é executada em uma Thread (linha de execução) independente para cada cliente.
    """
    apelido = "Desconhecido"
    try:
        # A PRIMEIRA mensagem enviada pelo cliente assim que ele conecta é o seu APELIDO
        dados_apelido = socket_cliente.recv(TAMANHO_BUFFER)
        if not dados_apelido:
            socket_cliente.close()
            return

        apelido = dados_apelido.decode("utf-8").strip()

        # Registra o cliente e seu apelido na lista do servidor
        with trava_clientes:
            clientes.append({"socket": socket_cliente, "apelido": apelido})

        msg_conexao = f"[SERVIDOR] Cliente conectado: {endereco_cliente} (Apelido: {apelido})"
        print(msg_conexao)
        registrar_evento(f"EVENTO: {apelido} conectou-se a partir de {endereco_cliente}")

        # Anuncia no chat que um novo usuário entrou
        msg_entrada = f"[SERVIDOR] {apelido} entrou no bate-papo!\n"
        retransmitir_mensagem(msg_entrada.encode("utf-8"), remetente_socket=socket_cliente)

        # 5) Laço principal de conversa: recebe uma mensagem, retransmite aos outros, repete.
        conversando = True
        while conversando:
            # recv() também pode retornar menos bytes do que o esperado;
            # para mensagens curtas de chat isso raramente é problema,
            # mas o HOWTO do Python alerta sobre esse comportamento.
            dados_recebidos = socket_cliente.recv(TAMANHO_BUFFER)

            # Segundo a documentação: quando recv() retorna 0 bytes,
            # significa que o outro lado fechou a conexão.
            if not dados_recebidos:
                print(f"[SERVIDOR] Cliente {apelido} desconectou.")
                registrar_evento(f"EVENTO: {apelido} desconectou-se.")
                break

            mensagem = dados_recebidos.decode("utf-8").strip()

            if mensagem.lower() == "sair":
                print(f"[SERVIDOR] Cliente {apelido} encerrou a conversa.")
                registrar_evento(f"EVENTO: {apelido} encerrou a conversa via comando 'sair'.")
                break

            # =========================================================
            # [MODIFICAÇÃO DO GRUPO] BOT DE COMANDOS E MENSAGEM PRIVADA
            # Se a mensagem começar com '/', é tratada como um comando.
            # =========================================================
            if mensagem.startswith("/"):
                comando_minusculo = mensagem.lower()

                if comando_minusculo == "/ajuda":
                    resposta_bot = (
                        "\n--- COMANDOS DO BATE-PAPO ---\n"
                        "/ajuda                 -> Mostra este menu de ajuda\n"
                        "/usuarios              -> Lista os usuários conectados no momento\n"
                        "/hora                  -> Exibe a hora exata do servidor\n"
                        "/msg <apelido> <texto> -> Envia uma mensagem privada\n"
                        "------------------------------------\n"
                    )
                    socket_cliente.sendall(resposta_bot.encode("utf-8"))

                elif comando_minusculo in ["/usuarios", "/online"]:
                    with trava_clientes:
                        lista_apelidos = [c["apelido"] for c in clientes]
                    total = len(lista_apelidos)
                    resposta_bot = f"[BOT]: Usuários online ({total}): {', '.join(lista_apelidos)}\n"
                    socket_cliente.sendall(resposta_bot.encode("utf-8"))

                elif comando_minusculo == "/hora":
                    hora_atual = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
                    resposta_bot = f"[BOT]: Data e hora no servidor: {hora_atual}\n"
                    socket_cliente.sendall(resposta_bot.encode("utf-8"))

                # [MODIFICAÇÃO DO GRUPO] SISTEMA DE MENSAGEM PRIVADA (DM)
                elif comando_minusculo.startswith("/msg "):
                    partes = mensagem.split(" ", 2)
                    if len(partes) < 3:
                        resposta_bot = "[BOT]: Uso correto: /msg <apelido> <mensagem>\n"
                        socket_cliente.sendall(resposta_bot.encode("utf-8"))
                    else:
                        destinatario_apelido = partes[1].strip()
                        mensagem_privada = partes[2].strip()

                        # Busca o socket do destinatário na lista de clientes
                        socket_destinatario = None
                        with trava_clientes:
                            for c in clientes:
                                if c["apelido"].lower() == destinatario_apelido.lower():
                                    socket_destinatario = c["socket"]
                                    break

                        if socket_destinatario:
                            # Envia apenas para o destinatário escolhido
                            msg_envio = f"[{apelido} te enviou uma mensagem privada]: {mensagem_privada}\n"
                            socket_destinatario.sendall(msg_envio.encode("utf-8"))

                            # Confirma o envio para o remetente
                            msg_confirma = f"[mensagem privada enviada para {destinatario_apelido}]: {mensagem_privada}\n"
                            socket_cliente.sendall(msg_confirma.encode("utf-8"))

                            # Registra log no console e na memória
                            print(f"[LOG de mensagens privadas] {apelido} -> {destinatario_apelido}: {mensagem_privada}")
                            registrar_evento(f"[LOG de mensagens privadas] {apelido} -> {destinatario_apelido}: {mensagem_privada}")
                        else:
                            resposta_bot = f"[BOT]: Usuário '{destinatario_apelido}' não foi encontrado ou está offline.\n"
                            socket_cliente.sendall(resposta_bot.encode("utf-8"))

                else:
                    resposta_bot = f"[BOT]: Comando '{mensagem}' não reconhecido. Digite /ajuda para ver as opções.\n"
                    socket_cliente.sendall(resposta_bot.encode("utf-8"))

                # Pula o restante do laço para NÃO retransmitir a linha do comando aos outros clientes
                continue

            # Formata a mensagem normal com o Apelido do cliente que enviou
            msg_formatada = f"[{apelido}]: {mensagem}\n"
            
            # Exibe a mensagem recebida no console e armazena na memória
            print(f"[{apelido}]: {mensagem}")
            registrar_evento(f"[{apelido}]: {mensagem}")

            # Retransmite a mensagem formatada para todos os outros clientes
            retransmitir_mensagem(msg_formatada.encode("utf-8"), remetente_socket=socket_cliente)

    except Exception as e:
        print(f"[SERVIDOR] Erro na conexão com {apelido}: {e}")
        registrar_evento(f"ERRO: Ocorreu uma falha na conexão com {apelido}: {e}")

    finally:
        # Remove o cliente da lista global ao desconectar
        with trava_clientes:
            for c in clientes:
                if c["socket"] == socket_cliente:
                    clientes.remove(c)
                    break

        # 6) Fecha os sockets ao final. O HOWTO reforça: sempre feche
        # explicitamente, não confie no coletor de lixo do Python para isso.
        socket_cliente.close()

        # Avisa aos demais participantes que o cliente saiu
        msg_saida = f"[SERVIDOR] {apelido} saiu do bate-papo.\n"
        retransmitir_mensagem(msg_saida.encode("utf-8"))


def iniciar_servidor():
    # 1) Cria o socket "tipo servidor".
    #    AF_INET  -> estamos usando endereços IPv4
    #    SOCK_STREAM -> estamos usando TCP (conexão confiável, com ordem garantida)
    socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Permite reiniciar o servidor rapidamente sem erro de "endereço em uso"
    socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # 2) Associa (bind) o socket a um endereço e porta específicos.
    socket_servidor.bind((HOST, PORTA))

    # 3) Coloca o socket em modo de escuta, esperando conexões.
    #    O número 5 é o tamanho máximo da fila de conexões pendentes.
    socket_servidor.listen(5)
    print(f"[SERVIDOR] Aguardando conexões em {HOST}:{PORTA}...\n")
    registrar_evento("--- SERVIDOR INICIADO ---")

    # Inicia a Thread para escutar o teclado do Servidor e permitir envio de mensagens/comandos
    thread_envio_servidor = threading.Thread(
        target=enviar_mensagens_servidor,
        daemon=True
    )
    thread_envio_servidor.start()

    # 4) accept() bloqueia a execução até um cliente se conectar.
    #    Retorna um NOVO socket (socket_cliente), específico para essa conversa,
    #    e o endereço de quem conectou.
    #    Em um servidor multi-cliente, colocamos accept() dentro de um laço
    #    e criamos uma Thread separada para cada conexão aceita.
    while True:
        try:
            socket_cliente, endereco_cliente = socket_servidor.accept()

            # Dispara uma nova thread independente para processar a conversa deste cliente
            thread_cliente = threading.Thread(
                target=tratar_cliente,
                args=(socket_cliente, endereco_cliente),
                daemon=True
            )
            thread_cliente.start()

        except KeyboardInterrupt:
            print("\n[SERVIDOR] Encerramento solicitado.")
            registrar_evento("--- SERVIDOR ENCERRADO PELO OPERADOR ---")
            break

    # 6) Fecha o socket principal do servidor ao encerrar o programa.
    socket_servidor.close()
    print("[SERVIDOR] Conexão encerrada.")


if __name__ == "__main__":
    iniciar_servidor()