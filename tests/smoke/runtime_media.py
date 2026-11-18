"""Offline functional check shared by the baseline and replacement media tools."""

import argparse
import array
import json
import os
import subprocess
import tempfile
import wave
from pathlib import Path


def run(*args):
    return subprocess.check_output(args, timeout=30)


def transcode(*args):
    return run("ffmpeg", "-nostdin", "-loglevel", "error", *args)


def probe(path):
    return json.loads(
        run("ffprobe", "-v", "error", "-show_streams", "-of", "json", path)
    )


def check(runtime):
    if runtime:
        if os.getuid() == 0:
            raise RuntimeError("Expected the production image's unprivileged user")
        versions = json.loads(Path("/usr/local/share/ffmpeg/versions.json").read_text())
        # Upstream fixed the issue in 2.11.0; Debian trixie's 'really2.9.14'
        # version is affected. Check inside the static build as well as dpkg.
        if tuple(map(int, versions["libxml2"].split("."))) < (2, 11, 0):
            raise RuntimeError(f"Affected embedded libxml2: {versions['libxml2']}")
        packages = run("dpkg-query", "-W", "-f=" + "${Package} ${db:Status-Status}\\n")
        if b"libxml2 installed" in packages.splitlines():
            raise RuntimeError("Unexpected Debian libxml2 runtime dependency")
        print("Embedded libxml2:", versions["libxml2"], "; Debian libxml2 absent")

    print(run("ffmpeg", "-version").decode().splitlines()[0])
    print(run("ffprobe", "-version").decode().splitlines()[0])
    with tempfile.TemporaryDirectory() as tmp:
        video, wav = (Path(tmp) / name for name in ("clip.mp4", "speech.wav"))
        transcode(
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=96x64:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            video,
        )
        streams = {s["codec_type"]: s for s in probe(video)["streams"]}
        v, a = streams["video"], streams["audio"]
        if (v["codec_name"], v["width"], v["height"], a["codec_name"]) != (
            "h264",
            96,
            64,
            "aac",
        ):
            raise RuntimeError("Unexpected muxed stream metadata")
        frames = transcode(
            "-i", video, "-map", "0:v:0", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"
        )
        size = 96 * 64 * 3
        if len(frames) != 10 * size or frames[:size] == frames[-size:]:
            raise RuntimeError("Decoded video frames missing or frozen")
        transcode(
            "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav
        )
        with wave.open(str(wav)) as reader:
            if (
                reader.getnchannels(),
                reader.getsampwidth(),
                reader.getframerate(),
            ) != (1, 2, 16000):
                raise RuntimeError("Wrong extracted PCM audio format")
            pcm = array.array("h", reader.readframes(reader.getnframes()))
        if not 15800 <= len(pcm) <= 16800 or max(pcm) < 1000:
            raise RuntimeError("Missing, silent, or truncated decoded audio")
        crosses = sum(
            left <= 0 < right
            for left, right in zip(pcm[1600:14399], pcm[1601:14400], strict=True)
        )
        if not 345 <= crosses <= 359:
            raise RuntimeError("Decoded signal does not match the 440 Hz input")
        if runtime:
            import cv2
            import ffmpeg

            if len(ffmpeg.probe(str(video))["streams"]) != 2:
                raise RuntimeError("Python ffmpeg binding could not probe both streams")
            capture = cv2.VideoCapture(str(video))
            try:
                ok, frame = capture.read()
                if not ok or frame.shape != (64, 96, 3):
                    raise RuntimeError("Application OpenCV frame extraction failed")
            finally:
                capture.release()
        print(
            f"PASS: H.264/AAC encode + probe, 10 decoded frames, {len(pcm)} mono PCM samples"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", action="store_true")
    check(parser.parse_args().runtime)
