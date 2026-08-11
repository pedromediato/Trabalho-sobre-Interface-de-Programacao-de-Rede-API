"""
cliente.py

Base do CLIENTE do trabalho de Sockets (Semana 1).
Referências utilizadas:
- https://docs.python.org/pt-br/3/howto/sockets.html
- https://docs.python.org/3/library/socket.html

Digite "sair" a qualquer momento para encerrar a conversa.
"""

import socket

# Precisam ser os MESMOS valores usados no servidor.py
HOST = "127.0.0.1"
PORTA = 8080
TAMANHO_BUFFER = 1024


def iniciar_cliente():
    # 1) Cria o socket "tipo cliente", igual ao do servidor:
    #    IPv4 (AF_INET) + TCP (SOCK_STREAM)
    socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 2) connect() estabelece a conexão com o servidor no endereço/porta indicados.
    socket_cliente.connect((HOST, PORTA))
    print(f"[CLIENTE] Conectado ao servidor em {HOST}:{PORTA}")
    print('[CLIENTE] Digite "sair" para encerrar a conversa.\n')

    conversando = True
    while conversando:
        mensagem = input("[CLIENTE] Sua mensagem: ")
        socket_cliente.sendall(mensagem.encode("utf-8"))

        if mensagem.lower() == "sair":
            conversando = False
            break

        # Espera a resposta do servidor
        dados_recebidos = socket_cliente.recv(TAMANHO_BUFFER)

        # recv() retornando vazio (b"") = a outra ponta fechou a conexão
        if not dados_recebidos:
            print("[CLIENTE] Servidor desconectou.")
            break

        resposta = dados_recebidos.decode("utf-8")
        print(f"[SERVIDOR] {resposta}")

        if resposta.lower() == "sair":
            conversando = False

    # 3) Fecha o socket ao final da conversa.
    socket_cliente.close()
    print("[CLIENTE] Conexão encerrada.")


if __name__ == "__main__":
    iniciar_cliente()