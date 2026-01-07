import cv2
import json
import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

def verify_and_execute(json_data, public_key):
    try:
        envelope = json.loads(json_data)
        payload = envelope['payload']
        signature = base64.b64decode(envelope['signature'])

        # Verify Signature
        data_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        public_key.verify(signature, data_bytes, ec.ECDSA(hashes.SHA256()))

        print(f"\n🟢 TRUSTED SIGNATURE VERIFIED: {envelope.get('signer_id', 'Unknown')}")
        print(f"🚀 EXECUTING: {payload.get('action')} -> {payload.get('tool')}")

        # In real life, put your MCP connection code here
        # For prototype:
        print(f"Args: {payload.get('args')}")

    except InvalidSignature:
        print("\n🔴 WARNING: Signature Invalid! Do not execute.")
    except Exception as e:
        print(f"⚠️ Error processing payload: {e}")

def run_listener(public_key_path="quantomcode_public.pem"):
    if not os.path.exists(public_key_path):
        print(f"❌ Public key not found at {public_key_path}. Cannot verify signatures.")
        return

    # Load Trusted Key
    with open(public_key_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    # Start Listener
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
         print("❌ Could not open video source (webcam).")
         return

    detector = cv2.QRCodeDetector()
    print("👀 Watching for UVAI Triggers... Press 'q' to quit.")

    while True:
        ret, img = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        data, bbox, _ = detector.detectAndDecode(img)

        if data:
            print(f"Found QR Code: {data[:50]}...")
            verify_and_execute(data, public_key)
            cv2.waitKey(2000) # Wait 2s to avoid double-trigger

        cv2.imshow("UVAI Listener", img)
        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_listener()
