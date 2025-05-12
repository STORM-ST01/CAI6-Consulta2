# client_znta/client.py

import json
import random
import requests
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from datetime import datetime
import socket

# -------- CONFIGURACIONES --------
PRIVATE_KEY_PATH = "client_znta/private_key.pem"
BROKER_URL = "http://127.0.0.1:5000/verify"   # Ajusta si el broker está en otro puerto/ip
NONCE = "example_nonce_123456"                # Simulado: en el flujo real, debería pedirse al Broker

# -------- FUNCIONES --------
def load_private_key(path):
    with open(path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key

def get_context_data():
    context = {
        "username": os.getenv("USER") or "usuario_demo",
        "role": "medico",  # uno de los roles permitidos
        "device_hardening_score": random.randint(60, 90),  # random para probar accesos permitidos o denegados
        "ip_address": get_ip_address(),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    return context

def get_ip_address():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
    except:
        ip = "127.0.0.1"
    return ip

def sign_nonce(private_key, nonce):
    signature = private_key.sign(
        nonce.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature.hex()  # Enviamos la firma como string hexadecimal

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
    signature = sign_nonce(private_key, NONCE)
    send_request(context_data, signature)
