# broker_znta/broker.py

from flask import Flask, request, jsonify
import csv
import os
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
import json

# -------- CONFIGURACIONES --------
CERTIFICATE_PATH = "broker_znta/certificate.crt"
POLICIES_PATH = "broker_znta/policies.json"  # Lo usarás luego para reglas de contexto
EXPECTED_NONCE = "example_nonce_123456"  # El mismo que el cliente usa (para esta demo)

app = Flask(__name__)

# -------- FUNCIONES --------

LOG_FILE = "broker_znta/access_logs.csv"

def log_access(context, result, reason):
    # Si el archivo no existe, escribir encabezado
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["timestamp", "ip_address", "username", "role", "hardening_score", "result", "reason"])
        
        writer.writerow([
            datetime.utcnow().isoformat() + "Z",
            context.get("ip_address", "unknown"),
            context.get("username", "unknown"),
            context.get("role", "unknown"),
            context.get("device_hardening_score", "unknown"),
            result,
            reason
        ])

def load_public_key(certificate_path):
    with open(certificate_path, "rb") as cert_file:
        cert_data = cert_file.read()
        cert = load_pem_x509_certificate(cert_data, backend=default_backend())
        public_key = cert.public_key()
    return public_key


def verify_signature(public_key, nonce, signature_hex):
    try:
        public_key.verify(
            bytes.fromhex(signature_hex),
            nonce.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        print(f"Error en la verificación de firma: {e}")
        return False

def validate_context(context):
    with open(POLICIES_PATH, "r") as f:
        policies = json.load(f)

    # Verificar rol permitido
    user_role = context.get("role")
    if user_role not in policies.get("allowed_roles", []):
        print(f"Acceso denegado: rol '{user_role}' no permitido.")
        return False

    # Verificar nivel de hardening
    device_hardening_score = context.get("device_hardening_score", 0)
    minimum_score = policies.get("minimum_hardening_score", 70)
    if device_hardening_score < minimum_score:
        print(f"Acceso denegado: hardening score {device_hardening_score} inferior al mínimo requerido ({minimum_score}).")
        return False

    # Verificar horario permitido
    timestamp = context.get("timestamp")
    if timestamp:
        try:
            from datetime import datetime
            access_time = datetime.fromisoformat(timestamp.replace("Z", "")).hour
            allowed_start = policies["allowed_hours"]["start"]
            allowed_end = policies["allowed_hours"]["end"]
            if not (allowed_start <= access_time <= allowed_end):
                print(f"Acceso denegado: hora {access_time} fuera del rango permitido.")
                return False
        except Exception as e:
            print(f"Error procesando la hora: {e}")
            return False
    else:
        print("Acceso denegado: timestamp no proporcionado.")
        return False

    return True


# -------- RUTA PRINCIPAL --------
@app.route("/verify", methods=["POST"])
def verify_access():
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "No JSON payload received"}), 400

    context = data.get("context")
    nonce = data.get("nonce")
    signature = data.get("signature")

    if nonce != EXPECTED_NONCE:
        log_access(context, "denied", "Nonce incorrecto")
        return jsonify({"status": "error", "message": "Nonce incorrecto"}), 400

    public_key = load_public_key(CERTIFICATE_PATH)

    if not verify_signature(public_key, nonce, signature):
        log_access(context, "denied", "Firma inválida")
        return jsonify({"status": "error", "message": "Firma inválida"}), 400

    if not validate_context(context):
        log_access(context, "denied", "Contexto no autorizado")
        return jsonify({"status": "error", "message": "Contexto no autorizado"}), 403

    log_access(context, "allowed", "Acceso autorizado")
    return jsonify({"status": "success", "message": "Access Allowed"}), 200


# -------- MAIN --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
