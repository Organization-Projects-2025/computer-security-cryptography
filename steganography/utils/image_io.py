# utils/image_io.py
from PIL import Image
import numpy as np

def load_image(path, mode="RGB"):
    img = Image.open(path).convert(mode)
    return img

def pil_to_numpy(img: Image.Image):
    return np.array(img)

def numpy_to_pil(arr: np.ndarray):
    return Image.fromarray(arr.astype("uint8"))

def normalize_for_torch(img_np: np.ndarray):
    # HWC uint8 -> CHW float32 [0,1]
    arr = img_np.astype("float32") / 255.0
    arr = np.transpose(arr, (2, 0, 1))
    return arr

def denormalize_from_torch(arr_chw: np.ndarray):
    # CHW [0,1] -> HWC uint8
    arr = np.clip(arr_chw, 0.0, 1.0)
    arr = np.transpose(arr, (1, 2, 0))
    arr = (arr * 255.0).round().astype("uint8")
    return arr
