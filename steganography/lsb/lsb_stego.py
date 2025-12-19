# lsb/lsb_stego.py
from PIL import Image
import numpy as np
from steganography import Steganography  # import from your friend's module

def lsb_hide(cover_img: np.ndarray, secret_img: np.ndarray) -> np.ndarray:
    """
    Use friend's hide_image_in_image logic but work in-memory.
    """
    # Convert numpy -> PIL and save to temp paths
    cover = Image.fromarray(cover_img.astype("uint8"))
    secret = Image.fromarray(secret_img.astype("uint8"))

    cover.save("tmp_cover.png")
    secret.save("tmp_secret.png")

    out_path = "tmp_stego.png"
    ok = Steganography.hide_image_in_image("tmp_cover.png", "tmp_secret.png", out_path)
    if not ok:
        raise RuntimeError("LSB hide failed")

    stego = np.array(Image.open(out_path).convert("RGB"))
    return stego

def lsb_reveal(stego_img: np.ndarray) -> np.ndarray:
    """
    Use friend's extract_image_from_image logic.
    """
    stego = Image.fromarray(stego_img.astype("uint8"))
    stego.save("tmp_stego_for_extract.png")

    out_path = "tmp_secret_rec.png"
    ok = Steganography.extract_image_from_image("tmp_stego_for_extract.png", out_path)
    if not ok:
        raise RuntimeError("LSB extract failed")

    secret_rec = np.array(Image.open(out_path).convert("RGB"))
    return secret_rec
