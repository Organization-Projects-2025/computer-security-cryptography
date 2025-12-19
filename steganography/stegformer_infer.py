# stegformer_infer.py
import numpy as np
import torch

from official.model import StegFormer
from official import config as official_config
from utils.image_io import normalize_for_torch, denormalize_from_torch


def _clean_state_dict(sd):
    """Remove profiling keys like total_ops/total_params so load_state_dict ignores them."""
    clean = {}
    for k, v in sd.items():
        # Skip pure profiling entries (they are tensors of counted ops/params)
        if "total_ops" in k or "total_params" in k:
            continue
        clean[k] = v
    return clean


class StegFormerInfer:
    def __init__(self, weights_path: str):
        """
        Wrapper for single-image hiding with StegFormer-S.
        Assumes checkpoint was trained with:
        - use_model = 'StegFormer-S'
        - num_secret = 1
        """
        args = official_config.Args()
        self.device = args.device

        # Force single secret, StegFormer-S, matching checkpoint shapes.
        self.num_secret = 1
        self.encoder = StegFormer(
            img_resolution=256,
            input_dim=6,
            cnn_emb_dim=8,
            output_dim=3,
            drop_key=False,
            patch_size=2,
            window_size=8,
            output_act=None,
            depth=[1,1,1,1,2,1,1,1,1],
            depth_tr=[2,2,2,2,2,2,2,2],
        )
        self.decoder = StegFormer(
            img_resolution=256,
            input_dim=3,
            cnn_emb_dim=8,
            output_dim=3,
            drop_key=False,
            patch_size=2,
            window_size=8,
            output_act=None,
            depth=[1,1,1,1,2,1,1,1,1],
            depth_tr=[2,2,2,2,2,2,2,2],
        )


        state = torch.load(weights_path, map_location=self.device)
        enc_sd = _clean_state_dict(state["encoder"])
        dec_sd = _clean_state_dict(state["decoder"])

        # strict=False to ignore remaining unexpected keys
        self.encoder.load_state_dict(enc_sd, strict=False)
        self.decoder.load_state_dict(dec_sd, strict=False)

        self.encoder.to(self.device).eval()
        self.decoder.to(self.device).eval()

    @torch.no_grad()
    def hide(self, cover_np: np.ndarray, secret_np: np.ndarray) -> np.ndarray:
        """
        cover_np, secret_np: HWC uint8, same shape.
        Returns stego image as HWC uint8.
        """
        if cover_np.shape != secret_np.shape:
            raise ValueError("Cover and secret must have the same size for StegFormer")

        cover_chw = normalize_for_torch(cover_np)
        secret_chw = normalize_for_torch(secret_np)

        msg = np.concatenate([cover_chw, secret_chw], axis=0)  # (6,H,W)
        msg_t = torch.from_numpy(msg).unsqueeze(0).to(self.device)  # (1,6,H,W)

        stego_t = self.encoder(msg_t).clamp(0.0, 1.0)
        stego_chw = stego_t.squeeze(0).cpu().numpy()
        stego_np = denormalize_from_torch(stego_chw)
        return stego_np

    @torch.no_grad()
    def reveal(self, stego_np: np.ndarray) -> np.ndarray:
        """
        stego_np: HWC uint8.
        Returns recovered secret as HWC uint8.
        """
        stego_chw = normalize_for_torch(stego_np)
        stego_t = torch.from_numpy(stego_chw).unsqueeze(0).to(self.device)  # (1,3,H,W)

        rec_t = self.decoder(stego_t).clamp(0.0, 1.0)
        rec_chw = rec_t.squeeze(0).cpu().numpy()
        rec_np = denormalize_from_torch(rec_chw)
        return rec_np
