"""
servidor.py

Base do SERVIDOR do trabalho de Sockets (Semana 1).
Referências utilizadas:
- https://docs.python.org/pt-br/3/howto/sockets.html
- https://docs.python.org/3/library/socket.html
- https://docs.python.org/3/library/threading.html

Nesta etapa, o código foi expandido de 1-para-1 para suportar múltiplos clientes
simultâneos com gerenciamento de apelidos, threads e envio de mensagens pelo próprio servidor.
"""
#matheus lindo maravilhoso
import socket
import threading

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
    [MODIFICAÇÃO DO GRUPO]
    Thread dedicada exclusivamente para permitir que o operador do servidor
    digite e envie mensagens de broadcast para todos os clientes conectados.
    """
    while True:
        try:
            mensagem = input()
            if mensagem.strip():
                msg_formatada = f"[SERVIDOR]: {mensagem}"
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

        print(f"[SERVIDOR] Cliente conectado: {endereco_cliente} (Apelido: {apelido})")

        # Anuncia no chat que um novo usuário entrou
        msg_entrada = f"[SERVIDOR] {apelido} entrou no bate-papo!"
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
                break

            mensagem = dados_recebidos.decode("utf-8")

            if mensagem.lower() == "sair":
                print(f"[SERVIDOR] Cliente {apelido} encerrou a conversa.")
                break

            # Formata a mensagem com o Apelido do cliente que enviou
            msg_formatada = f"[{apelido}]: {mensagem}"
            
            # Exibe a mensagem recebida diretamente no console do servidor
            print(msg_formatada)

            # Retransmite a mensagem formatada para todos os outros clientes
            retransmitir_mensagem(msg_formatada.encode("utf-8"), remetente_socket=socket_cliente)

    except Exception as e:
        print(f"[SERVIDOR] Erro na conexão com {apelido}: {e}")

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
        msg_saida = f"[SERVIDOR] {apelido} saiu do bate-papo."
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

    # [MODIFICAÇÃO DO GRUPO]
    # Inicia a Thread para escutar o teclado do Servidor e permitir envio de mensagens
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
            break

    # 6) Fecha o socket principal do servidor ao encerrar o programa.
    socket_servidor.close()
    print("[SERVIDOR] Conexão encerrada.")


if __name__ == "__main__":
    iniciar_servidor()