# client_znta/bulk_test_client.py

import json
import requests
import os
import random
import platform
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

try:
    import wmi  # Solo funciona en Windows
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

# -------- CONFIG --------
PRIVATE_KEY_PATH = "client_znta/private_key.pem"
BROKER_URL = "http://127.0.0.1:5000/verify"
NONCE = "example_nonce_123456"
NUMBER_OF_ATTEMPTS = 50

# -------- FUNCIONES --------
def load_private_key(path):
    with open(path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key

def generate_random_timestamp():
    random_hour = random.randint(6, 23)
    now = datetime.utcnow()
    random_time = now.replace(hour=random_hour, minute=random.randint(0, 59), second=random.randint(0, 59))
    return random_time.isoformat() + "Z"

def detect_real_os():
    system = platform.system()
    release = platform.release()
    return f"{system} {release}"

def detect_antivirus_status():
    if WMI_AVAILABLE:
        try:
            c = wmi.WMI(namespace="root\SecurityCenter2")
            for av in c.AntiVirusProduct():
                if av.productState:  # Si hay antivirus con algún estado
                    return True
            return False
        except Exception:
            return False
    else:
        return random.choice([True, False])  # Si no hay WMI, simula

def random_context(user_number):
    roles = ["medico", "farmaceutico", "administrativo", "hacker", "invitado"]
    accepted_os = ["Windows 10", "Windows 11" "Ubuntu 22.04", "macOS Ventura"]
    random_os_pool = accepted_os + ["Windows XP", "Android", "Kali Linux"]

    username = f"user{user_number}"
    role = random.choice(roles)
    hardening_score = random.randint(50, 95)
    ip_address = "127.0.0.1"
    timestamp = generate_random_timestamp()

    # OS decision: 50% real, 50% random
    if random.random() < 0.5:
        device_os = detect_real_os()
    else:
        device_os = random.choice(random_os_pool)

    # Antivirus decision: 50% real, 50% random
    if random.random() < 0.5:
        antivirus_active = detect_antivirus_status()
    else:
        antivirus_active = random.choice([True, False])

    # Parches sistema (simulado)
    system_patched = random.choice([True, False])

    context = {
        "username": username,
        "role": role,
        "device_hardening_score": hardening_score,
        "ip_address": ip_address,
        "timestamp": timestamp,
        "device_os": device_os,
        "antivirus_active": antivirus_active,
        "system_patched": system_patched
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
    return response.status_code, response.text

# -------- MAIN --------
if __name__ == "__main__":
    private_key = load_private_key(PRIVATE_KEY_PATH)
    
    for i in range(1, NUMBER_OF_ATTEMPTS + 1):
        context = random_context(i)
        signature = sign_nonce(private_key, NONCE)
        status, text = send_request(context, signature)
        
        print(f"[{i}] {context['username']} ({context['role']}) - OS: {context['device_os']} - Antivirus: {context['antivirus_active']} - Hardening: {context['device_hardening_score']} - Hora: {context['timestamp']} --> {text}")
