"""
cliente.py

Base do CLIENTE do trabalho de Sockets (Semana 1).
Referências utilizadas:
- https://docs.python.org/pt-br/3/howto/sockets.html
- https://docs.python.org/3/library/socket.html
- https://docs.python.org/3/library/threading.html

Digite "sair" a qualquer momento para encerrar a conversa.
"""

import socket
import threading

# Precisam ser os MESMOS valores usados no servidor.py
HOST = "127.0.0.1"
PORTA = 8080
TAMANHO_BUFFER = 1024


def escutar_servidor(socket_cliente, apelido):
    """
    Thread dedicada exclusivamente a escutar e exibir as respostas e mensagens
    vindas do servidor sem bloquear o input do usuário.
    """
    while True:
        try:
            # Espera a resposta do servidor
            dados_recebidos = socket_cliente.recv(TAMANHO_BUFFER)

            # recv() retornando vazio (b"") = a outra ponta fechou a conexão
            if not dados_recebidos:
                print(f"\n[{apelido}] Servidor desconectou.")
                break

            resposta = dados_recebidos.decode("utf-8")
            print(f"\n{resposta}")
            print(f"[{apelido}] Sua mensagem: ", end="", flush=True)

        except:
            break


def iniciar_cliente():
    # Solicita o apelido do usuário antes de conectar
    apelido = input("Digite seu apelido para entrar no chat: ").strip()
    while not apelido:
        apelido = input("O apelido não pode ser vazio! Digite seu apelido: ").strip()

    # 1) Cria o socket "tipo cliente", igual ao do servidor:
    #    IPv4 (AF_INET) + TCP (SOCK_STREAM)
    socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # 2) connect() estabelece a conexão com o servidor no endereço/porta indicados.
        socket_cliente.connect((HOST, PORTA))
        print(f"[{apelido}] Conectado ao servidor em {HOST}:{PORTA}")

        # Envia o Apelido como a primeira mensagem de identificação para o servidor
        # sendall() garante que todos os bytes sejam enviados,
        # tratando internamente o que o HOWTO chama de "não enviar tudo de uma vez"
        socket_cliente.sendall(apelido.encode("utf-8"))

        print(f'[{apelido}] Bem-vindo(a), {apelido}! Digite "sair" para encerrar a conversa.\n')

        # Inicia a Thread para escutar mensagens recebidas do servidor em segundo plano
        thread_escuta = threading.Thread(
            target=escutar_servidor,
            args=(socket_cliente, apelido),
            daemon=True
        )
        thread_escuta.start()

        conversando = True
        while conversando:
            mensagem = input(f"[{apelido}] Sua mensagem: ")

            if not mensagem.strip():
                continue

            # sendall() garante que todos os bytes sejam enviados,
            # tratando internamente o que o HOWTO chama de "não enviar tudo de uma vez"
            socket_cliente.sendall(mensagem.encode("utf-8"))

            if mensagem.lower() == "sair":
                conversando = False
                break

    except Exception as e:
        print(f"[{apelido}] Erro ao conectar: {e}")

    finally:
        # 3) Fecha o socket ao final da conversa.
        socket_cliente.close()
        print(f"[{apelido}] Conexão encerrada.")


if __name__ == "__main__":
    iniciar_cliente()