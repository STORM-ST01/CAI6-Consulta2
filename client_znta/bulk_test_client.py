# client_znta/bulk_test_client.py

import json
import requests
import os
import random
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

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

def random_context(user_number):
    roles = ["medico", "farmaceutico", "administrativo", "hacker", "invitado"]
    username = f"user{user_number}"
    role = random.choice(roles)
    hardening_score = random.randint(50, 95)
    ip_address = "127.0.0.1"
    timestamp = generate_random_timestamp()
    
    context = {
        "username": username,
        "role": role,
        "device_hardening_score": hardening_score,
        "ip_address": ip_address,
        "timestamp": timestamp
    }
    return context

def generate_random_timestamp():
    # Hora random entre 6 y 23
    random_hour = random.randint(6, 23)
    now = datetime.utcnow()
    random_time = now.replace(hour=random_hour, minute=random.randint(0, 59), second=random.randint(0, 59))
    return random_time.isoformat() + "Z"

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
        
        print(f"[{i}] {context['username']} ({context['role']}) - Hardening: {context['device_hardening_score']} - Hora: {context['timestamp']} --> {text}")
