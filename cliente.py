"""
cliente.py - Cliente Bate-Papo no Terminal com Protocolo JSON

Este código permite testar a comunicação JSON antes de montarmos a Interface Gráfica!
"""

import socket
import threading
import json
import sys

HOST = "127.0.0.1"
PORTA = 8080


def receber_mensagens(sock):
    """
    Thread dedicada exclusivamente a ESCUTAR os dados enviados pelo servidor.
    Lê os bytes, remonta as mensagens separadas por '\n' e decodifica os pacotes JSON.
    """
    buffer_dados = ""
    while True:
        try:
            dados_brutos = sock.recv(2048).decode("utf-8")
            if not dados_brutos:
                print("\n[SISTEMA] Conexão com o servidor foi encerrada.")
                break

            # Acumula fragmentos no buffer
            buffer_dados += dados_brutos

            # Processa linha por linha delimitada por '\n'
            while "\n" in buffer_dados:
                linha_json, buffer_dados = buffer_dados.split("\n", 1)
                if not linha_json.strip():
                    continue

                # Decodifica a string JSON recebida para um Dicionário Python
                pacote = json.loads(linha_json)
                tipo = pacote.get("tipo")

                # Trata a exibição de acordo com o TIPO da mensagem recebida
                if tipo == "mensagem":
                    hora = pacote.get("hora", "")
                    remetente = pacote.get("remetente", "")
                    texto = pacote.get("texto", "")
                    print(f"\n[{hora}] [{remetente}]: {texto}")

                elif tipo == "msg_privada":
                    hora = pacote.get("hora", "")
                    remetente = pacote.get("remetente", "")
                    texto = pacote.get("texto", "")
                    print(f"\n[{hora}] [PRIVADO de {remetente}]: {texto}")

                elif tipo == "sistema":
                    print(f"\n[SISTEMA]: {pacote.get('texto')}")

                elif tipo == "lista_usuarios":
                    usuarios = pacote.get("usuarios", [])
                    print(f"\n[SISTEMA - Usuários Online ({len(usuarios)})]: {', '.join(usuarios)}")

        except Exception as e:
            print(f"\n[ERRO]: Falha na recepção de dados: {e}")
            break


def iniciar_cliente():
    """
    Função principal do cliente: estabelece conexão, envia o apelido inicial
    e mantém o loop de digitação do teclado.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORTA))
    except Exception as e:
        print(f"Não foi possível conectar ao servidor {HOST}:{PORTA} -> {e}")
        sys.exit()

    # Pergunta o apelido ao usuário antes de liberar o chat
    apelido = input("Digite seu apelido para entrar no chat: ").strip()
    
    # 1) Envia o primeiro pacote JSON de CONEXÃO notificando o apelido escolhido
    pacote_conexao = json.dumps({"tipo": "conexao", "apelido": apelido}) + "\n"
    sock.sendall(pacote_conexao.encode("utf-8"))

    # 2) Dispara a thread em segundo plano para escutar respostas do servidor
    thread_rec = threading.Thread(target=receber_mensagens, args=(sock,), daemon=True)
    thread_rec.start()

    print("\nConectado com sucesso! Digite suas mensagens ou /ajuda para comandos.\n")

    # 3) Loop principal para ler o teclado e enviar mensagens como JSON
    while True:
        try:
            texto = input()
            if not texto.strip():
                continue

            # Monta o pacote de mensagem no formato JSON
            pacote_envio = json.dumps({"tipo": "mensagem", "texto": texto}) + "\n"
            sock.sendall(pacote_envio.encode("utf-8"))

            if texto.lower() == "sair":
                break
        except KeyboardInterrupt:
            break

    sock.close()


if __name__ == "__main__":
    iniciar_cliente()