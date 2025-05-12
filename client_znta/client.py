# client_znta/client.py

import json
import random
import requests
import os
import socket
import platform
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from datetime import datetime

try:
    import wmi  # Solo si estás en Windows
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

# -------- CONFIGURACIONES --------
PRIVATE_KEY_PATH = "client_znta/private_key.pem"
BROKER_URL = "http://127.0.0.1:5000/verify"   # Ajusta si el broker está en otro puerto/ip
NONCE = "example_nonce_123456"                # Simulado: en flujo real se debería pedir dinámicamente

# -------- FUNCIONES --------
def load_private_key(path):
    with open(path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key

def get_ip_address():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
    except:
        ip = "127.0.0.1"
    return ip

def detect_real_os():
    system = platform.system()
    release = platform.release()
    return f"{system} {release}"

def detect_antivirus_status():
    if WMI_AVAILABLE:
        try:
            c = wmi.WMI(namespace="root\SecurityCenter2")
            antiviruses = c.AntiVirusProduct()
            return len(antiviruses) > 0
        except Exception:
            return False
    else:
        return False  # No WMI disponible o no Windows

def get_context_data():
    context = {
        "username": os.getenv("USER") or os.getenv("USERNAME") or "usuario_demo",
        "role": "medico",  # uno de los roles permitidos
        "device_hardening_score": random.randint(70, 90),  # puntuación razonable para pasar políticas
        "ip_address": get_ip_address(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "device_os": detect_real_os(),
        "antivirus_active": detect_antivirus_status(),
        "system_patched": random.choice([True, False])  # Simulamos parches (complejo detectar de verdad)
    }
    return context

def sign_nonce(private_key, nonce):
    signature = private_key.sign(
        nonce.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature.hex()

def send_request(context, signature):
    payload = {
        "context": context,
        "nonce": NONCE,
        "signature": signature
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(BROKER_URL, data=json.dumps(payload), headers=headers)
    print(f"Respuesta del broker: {response.text}")

# -------- MAIN --------
if __name__ == "__main__":
    private_key = load_private_key(PRIVATE_KEY_PATH)
    context_data = get_context_data()
    
    print("\n➡️  Datos del cliente generados:")
    for key, value in context_data.items():
        print(f"{key}: {value}")
    
    signature = sign_nonce(private_key, NONCE)
    send_request(context_data, signature)
    
    print(platform.system())
    print(platform.release())
    print(platform.version())
    print(platform.platform())
    print(platform.uname())
