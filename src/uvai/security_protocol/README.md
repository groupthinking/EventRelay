# UVAI Secure Video Protocol

This module implements a cryptographically secure method for embedding executable actions within video content using standard QR codes and ECDSA signatures. This allows for a "sealed" instruction set that agents can trust and execute automatically.

## Overview

The system consists of three parts:

1.  **Identity Generation (`generate_keys.py`)**: Creates an ECDSA key pair. The private key signs the video; the public key verifies it.
2.  **Video Encoder (`encode_video.py`)**: Takes a JSON action payload, signs it, generates a QR code, and overlays it onto a video. It also embeds the payload in the video metadata.
3.  **Agent Listener (`video_listener.py`)**: Watches a video stream (e.g., webcam), detects the QR code, verifies the signature against the trusted public key, and executes the action.

## Prerequisites

Install the required dependencies:

```bash
pip install cryptography ffmpeg-python qrcode[pil] opencv-python
```

You also need `ffmpeg` installed on your system.

## Usage

### 1. Generate Your "Golden Keys"

Run this once to create your identity.

```bash
python generate_keys.py
```

This generates:

- `uvai_private.pem`: **KEEP SECRET**. Used to sign videos.
- `uvai_public.pem`: **DISTRIBUTE**. Used by agents to verify you.

### 2. Sign and Encode a Video

Update the `my_action` payload in `encode_video.py` or import the function.

```bash
python encode_video.py
```

- Input: `input.mp4` (Must exist in the directory)
- Output: `output_signed.mp4`

### 3. Run the Listener

Start the agent listener. It will use your webcam to scan for signed QR codes.

```bash
python video_listener.py
```

Point your camera at `output_signed.mp4` playing on a screen. If the signature is valid, the agent will verify and execute the action.

## Security Architecture

- **Algorithm**: ECDSA (NIST P-256 curve) with SHA-256.
- **Efficiency**: ECDSA signatures are small (~64 bytes), allowing for denser QR codes suitable for video scanning.
- **Trust Model**: The agent only executes actions signed by a key in its local "Trusted Signers" list (currently `uvai_public.pem`).
