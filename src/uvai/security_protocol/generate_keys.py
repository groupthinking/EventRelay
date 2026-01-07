from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import os

def generate_keys():
    # 1. Generate Keys
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Determine paths (save in current directory or specific keys dir)
    # Using current working directory for simplicity as per snippet

    # 2. Save Private Key (For YOU only - used to sign videos)
    with open("uvai_private.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # 3. Save Public Key (For USERS - used to verify you)
    with open("uvai_public.pem", "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    print(f"✅ Keys Generated in {os.getcwd()}.")
    print("'uvai_private.pem' is your stamp. 'uvai_public.pem' goes to the user.")

if __name__ == "__main__":
    generate_keys()
