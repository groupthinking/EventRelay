from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import os

def generate_key_pair():
    # 1. Generate the Private Key (using NIST P-256 curve)
    private_key = ec.generate_private_key(ec.SECP256R1())

    # 2. Serialize Private Key (Save to file)
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption() # In production, add a password here!
    )

    with open("quantomcode_private.pem", "wb") as f:
        f.write(pem_private)

    # 3. Generate Public Key
    public_key = private_key.public_key()

    # 4. Serialize Public Key (Save to file)
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open("quantomcode_public.pem", "wb") as f:
        f.write(pem_public)

    print("✅ KEYS GENERATED!")
    print(f"🔒 Private Key: {os.path.abspath('quantomcode_private.pem')} (KEEP SAFE)")
    print(f"🌍 Public Key:  {os.path.abspath('quantomcode_public.pem')} (DISTRIBUTE)")

if __name__ == "__main__":
    generate_key_pair()
