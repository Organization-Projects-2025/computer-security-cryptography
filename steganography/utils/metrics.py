# utils/metrics.py
import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

def compute_psnr(img1: np.ndarray, img2: np.ndarray):
    return peak_signal_noise_ratio(img1, img2, data_range=255)

def compute_ssim(img1: np.ndarray, img2: np.ndarray):
    return structural_similarity(img1, img2, channel_axis=2, data_range=255)
