# Secure Video Protocol Test Plan

## Objective

Verify the end-to-end functionality of the UVAI Secure Video Protocol: Key Generation -> Video Signing (QR Embedding) -> Verification & Execution.

## Steps

1.  **Environment Setup**: Install necessary Python dependencies (`cryptography`, `ffmpeg-python`, `qrcode`, `opencv-python`).
2.  **Key Generation**: Execute `generate_keys.py` to create the ECDSA key pair (`uvai_private.pem`, `uvai_public.pem`).
3.  **Input Creation**: Generate a specific dummy video file (`input.mp4`) using `ffmpeg` to serve as the carrier.
4.  **Signing & Encoding**: Execute `encode_video.py` to embed a signed payload into the video, creating `output_signed.mp4`.
5.  **Verification (Simulation)**: Create and run a test script (`test_listener_file.py`) that feeds `output_signed.mp4` into the listener logic (simulating a camera feed) to verify:
    - QR Code detection.
    - Signature verification against the public key.
    - Payload extraction.

## Expected Outcome

The test script should output:
`🟢 TRUSTED SIGNATURE VERIFIED: QuantomCode_Official`
`🚀 EXECUTING: call_tool -> create_file`
