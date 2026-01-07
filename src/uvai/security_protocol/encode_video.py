import ffmpeg
import qrcode
import json
import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

def sign_and_encode_video(input_video, output_video, action_payload, private_key_path="uvai_private.pem"):
    # --- STEP A: SIGN THE PAYLOAD ---
    print("🔐 Signing Payload...")
    if not os.path.exists(private_key_path):
        raise FileNotFoundError(f"Private key not found at {private_key_path}. Run generate_keys.py first.")

    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)

    # Sort keys for consistent hashing
    data_bytes = json.dumps(action_payload, sort_keys=True).encode('utf-8')
    signature = private_key.sign(data_bytes, ec.ECDSA(hashes.SHA256()))

    final_envelope = {
        "payload": action_payload,
        "signature": base64.b64encode(signature).decode('utf-8'),
        "signer_id": "QuantomCode_Official"
    }

    json_str = json.dumps(final_envelope)

    # --- STEP B: GENERATE QR CODE ---
    print("🔳 Generating QR...")
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(json_str)
    qr.make(fit=True)
    temp_qr_path = "temp_qr.png"
    qr.make_image(fill_color="black", back_color="white").save(temp_qr_path)

    # --- STEP C: EMBED INTO VIDEO (VISUAL + METADATA) ---
    print("🎬 Rendering Video...")
    try:
        # Get video dimensions to calculate position (W-w-10, H-h-10 ensures bottom right)
        # Using ffmpeg-python complex filter
        # Note: This requires ffmpeg installed on system and ffmpeg-python

        # Simple overlay
        stream = ffmpeg.input(input_video)
        overlay_file = ffmpeg.input(temp_qr_path)

        # 'W-w-10:H-h-10' positions it 10 pixels from bottom right
        # We need to ensure we're not overwriting input

        (
            stream
            .overlay(overlay_file, x='W-w-10', y='H-h-10')
            .output(output_video, **{'metadata:g': f'comment={json_str}'})
            .run(overwrite_output=True, quiet=True)
        )
        print(f"✅ Success! Created '{output_video}' with signed payload.")
    except Exception as e:
        print(f"❌ FFmpeg Error: {e}")
        # Re-raise to alert caller
        raise
    finally:
        if os.path.exists(temp_qr_path):
            os.remove(temp_qr_path)

if __name__ == "__main__":
    # Example Usage
    my_action = {
        "protocol": "uvai",
        "action": "call_tool",
        "tool": "create_file",
        "args": {"path": "success.txt", "content": "It works!"}
    }

    # Check for dummy input
    if os.path.exists('input.mp4'):
        sign_and_encode_video('input.mp4', 'output_signed.mp4', my_action)
    else:
        print("⚠️ No input.mp4 found. Please provide an input video execution.")
