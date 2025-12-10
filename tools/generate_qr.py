#!/usr/bin/env python3
"""
Generate a QR code PNG for a given URL (defaults to this repository).

Usage:
    python tools/generate_qr.py                # writes ./instacart_repo_qr.png
    python tools/generate_qr.py --url <URL>   # write QR for custom URL
    python tools/generate_qr.py --out path.png

Dependencies:
    pip install qrcode[pil]

This script uses the `qrcode` library and Pillow to render a PNG file.
"""
import argparse
from pathlib import Path

DEFAULT_URL = "https://github.com/boratonAJ/InstacartApp"
DEFAULT_OUT = Path("InstacartApp/instacart_repo_qr.png")


def make_qr(url: str, out_path: Path, scale: int = 10, border: int = 4):
    try:
        import qrcode
    except ImportError:
        raise

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=scale,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Generate a QR code PNG for a repository or URL.")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="URL to encode (default: repo)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output PNG path")
    parser.add_argument("--scale", type=int, default=10, help="scale/box size for QR code")
    parser.add_argument("--border", type=int, default=4, help="quiet zone border size")

    args = parser.parse_args()

    try:
        out = make_qr(args.url, args.out, scale=args.scale, border=args.border)
        print(f"Wrote QR code for {args.url} -> {out}")
    except ImportError:
        print("Missing dependency: install with `pip install qrcode[pil]` and try again.")


if __name__ == "__main__":
    main()
