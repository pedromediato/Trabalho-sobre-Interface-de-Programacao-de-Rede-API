import subprocess
import sys
import time

try:
    # sys.executable força o uso do mesmo Python do VS Code
    servidor = subprocess.Popen([sys.executable, "servidor.py"])
    time.sleep(1)

    cliente1 = subprocess.Popen([sys.executable, "cliente_gui.py"])
    cliente2 = subprocess.Popen([sys.executable, "cliente_gui.py"])

    cliente1.wait()
    cliente2.wait()

except KeyboardInterrupt:
    print("\n[!] Interrupção manual detectada.")

finally:
    print("[*] Encerrando o servidor e todos os clientes...")
    for processo in [servidor, cliente1, cliente2]:
        if "processo" in locals() and processo.poll() is None:
            processo.terminate()
    print("[✓] Tudo finalizado com sucesso!")