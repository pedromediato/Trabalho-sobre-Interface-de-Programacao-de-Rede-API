"""
servidor.py

Base do SERVIDOR do trabalho de Sockets (Semana 1).
Referências utilizadas:
- https://docs.python.org/pt-br/3/howto/sockets.html
- https://docs.python.org/3/library/socket.html

Nesta etapa (Semana 1), o objetivo é o mais simples possível:
1 servidor conversando com 1 cliente, no mesmo computador (localhost).
As próximas semanas vão adicionar: múltiplos clientes (threading),
interface gráfica (tkinter) e comandos especiais.
"""

import socket

# --- Configurações básicas ---
# Segundo o HOWTO do Python, portas baixas (abaixo de 1024) costumam ser
# reservadas para serviços conhecidos (HTTP, FTP, etc). Por isso usamos
# uma porta alta, como 8080.
HOST = "127.0.0.1"  # localhost -> só aceita conexões da própria máquina
PORTA = 8080
TAMANHO_BUFFER = 1024  # quantidade de bytes lidos por vez no recv()


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
    print(f"[SERVIDOR] Aguardando conexões em {HOST}:{PORTA}...")

    # 4) accept() bloqueia a execução até um cliente se conectar.
    #    Retorna um NOVO socket (socket_cliente), específico para essa conversa,
    #    e o endereço de quem conectou.
    socket_cliente, endereco_cliente = socket_servidor.accept()
    print(f"[SERVIDOR] Cliente conectado: {endereco_cliente}")

    # 5) Laço principal de conversa: recebe uma mensagem, responde, repete.
    conversando = True
    while conversando:
        # recv() também pode retornar menos bytes do que o esperado;
        # para mensagens curtas de chat isso raramente é problema,
        # mas o HOWTO do Python alerta sobre esse comportamento.
        dados_recebidos = socket_cliente.recv(TAMANHO_BUFFER)

        # Segundo a documentação: quando recv() retorna 0 bytes,
        # significa que o outro lado fechou a conexão.
        if not dados_recebidos:
            print("[SERVIDOR] Cliente desconectou.")
            break

        mensagem = dados_recebidos.decode("utf-8")
        print(f"[CLIENTE] {mensagem}")

        if mensagem.lower() == "sair":
            print("[SERVIDOR] Cliente encerrou a conversa.")
            break

        # Responde ao cliente
        resposta = input("[SERVIDOR] Sua resposta: ")
        # sendall() garante que todos os bytes sejam enviados,
        # tratando internamente o que o HOWTO chama de "não enviar tudo de uma vez"
        socket_cliente.sendall(resposta.encode("utf-8"))

        if resposta.lower() == "sair":
            conversando = False

    # 6) Fecha os sockets ao final. O HOWTO reforça: sempre feche
    # explicitamente, não confie no coletor de lixo do Python para isso.
    socket_cliente.close()
    socket_servidor.close()
    print("[SERVIDOR] Conexão encerrada.")


if __name__ == "__main__":
    iniciar_servidor()