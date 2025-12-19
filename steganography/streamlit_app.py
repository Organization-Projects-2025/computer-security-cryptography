# streamlit_app.py
import io
import zipfile
import datetime
import time  # ADD THIS

import streamlit as st
from PIL import Image

from utils.image_io import pil_to_numpy, numpy_to_pil
from utils.metrics import compute_psnr, compute_ssim
from lsb.lsb_stego import lsb_hide, lsb_reveal
from stegformer_infer import StegFormerInfer

STEGO_SIZE = (256, 256)
DISPLAY_WIDTH = 220  # image width in UI

@st.cache_resource
def load_stegformer(weights_path: str):
    return StegFormerInfer(weights_path)

def resize_256(img: Image.Image) -> Image.Image:
    return img.resize(STEGO_SIZE, Image.BICUBIC)

def build_zip(cover_np, secret_np, results, metrics_all):
    """
    Build a ZIP file in memory containing:
      - cover_256.png
      - secret_256.png
      - <algo>_stego.png
      - <algo>_recovered.png
      - metrics.csv
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # inputs
        cov_buf = io.BytesIO()
        numpy_to_pil(cover_np).save(cov_buf, format="PNG")
        zf.writestr("cover_256.png", cov_buf.getvalue())

        sec_buf = io.BytesIO()
        numpy_to_pil(secret_np).save(sec_buf, format="PNG")
        zf.writestr("secret_256.png", sec_buf.getvalue())

        # per‑algorithm outputs
        for name, (stego_np, rec_np, _) in results.items():
            s_buf = io.BytesIO()
            numpy_to_pil(stego_np).save(s_buf, format="PNG")
            zf.writestr(f"{name.lower()}_stego.png", s_buf.getvalue())

            r_buf = io.BytesIO()
            numpy_to_pil(rec_np).save(r_buf, format="PNG")
            zf.writestr(f"{name.lower()}_recovered.png", r_buf.getvalue())

        # metrics.csv - ADD INFERENCE TIME
        csv_buf = io.StringIO()
        csv_buf.write("algorithm,cover_psnr,cover_ssim,secret_psnr,secret_ssim,inference_time_ms\n")
        for name, m in metrics_all.items():
            if m is None:
                continue
            csv_buf.write(
                f"{name},{m['cov_psnr']:.4f},{m['cov_ssim']:.4f},"
                f"{m['sec_psnr']:.4f},{m['sec_ssim']:.4f},{m['inference_time']:.2f}\n"
            )
        zf.writestr("metrics.csv", csv_buf.getvalue())

    buf.seek(0)
    return buf

def main():
    st.set_page_config(page_title="Steganography Lab", layout="wide")
    st.title("Steganography Comparison: LSB vs StegFormer")

    # ---------- load model once ----------
    weights_path = "weights/StegFormer-S_baseline.pt"  # adjust this path
    stegformer = load_stegformer(weights_path)

    # ---------- session state for results ----------
    if "lsb_result" not in st.session_state:
        st.session_state.lsb_result = None  # (stego_np, rec_np, metrics_dict)
    if "steg_result" not in st.session_state:
        st.session_state.steg_result = None

    # ---------- inputs ----------
    st.subheader("1. Upload images (256×256 comparison)")

    col_cover, col_secret = st.columns(2, gap="small")
    with col_cover:
        cover_file = st.file_uploader(
            "Cover image",
            type=["png", "jpg", "jpeg", "bmp"],
            key="cover_uploader",
        )
    with col_secret:
        secret_file = st.file_uploader(
            "Secret image",
            type=["png", "jpg", "jpeg", "bmp"],
            key="secret_uploader",
        )

    if not (cover_file and secret_file):
        st.info("Upload both cover and secret images to run comparisons.")
        return

    cover_pil = resize_256(Image.open(cover_file).convert("RGB"))
    secret_pil = resize_256(Image.open(secret_file).convert("RGB"))
    cover_np = pil_to_numpy(cover_pil)
    secret_np = pil_to_numpy(secret_pil)

    st.write("Preview (both resized to 256×256):")
    p1, p2 = st.columns(2, gap="small")
    with p1:
        st.image(cover_pil, caption="Cover (256×256)", width=DISPLAY_WIDTH)
    with p2:
        st.image(secret_pil, caption="Secret (256×256)", width=DISPLAY_WIDTH)

    # ---------- 2. Run algorithms ----------
    st.markdown("---")
    st.subheader("2. Run algorithms")

    c_run1, c_run2, _ = st.columns([1, 1, 4], gap="small")
    with c_run1:
        run_lsb = st.button("Run LSB")
    with c_run2:
        run_steg = st.button("Run StegFormer")

    # Only recompute when button is pressed; otherwise keep previous results
    if run_lsb:
        with st.spinner("Running LSB..."):
            start_time = time.time()
            stego = lsb_hide(cover_np, secret_np)
            rec = lsb_reveal(stego)
            inference_time = (time.time() - start_time) * 1000  # ms
            
            cov_psnr = compute_psnr(cover_np, stego)
            cov_ssim = compute_ssim(cover_np, stego)
            sec_psnr = compute_psnr(secret_np, rec)
            sec_ssim = compute_ssim(secret_np, rec)
            m = dict(
                cov_psnr=cov_psnr,
                cov_ssim=cov_ssim,
                sec_psnr=sec_psnr,
                sec_ssim=sec_ssim,
                inference_time=inference_time,  # ADD THIS
            )
            st.session_state.lsb_result = (stego, rec, m)

    if run_steg:
        with st.spinner("Running StegFormer..."):
            start_time = time.time()
            cov = cover_np
            sec = secret_np
            stego = stegformer.hide(cov, sec)
            rec = stegformer.reveal(stego)
            inference_time = (time.time() - start_time) * 1000  # ms
            
            cov_psnr = compute_psnr(cov, stego)
            cov_ssim = compute_ssim(cov, stego)
            sec_psnr = compute_psnr(sec, rec)
            sec_ssim = compute_ssim(sec, rec)
            m = dict(
                cov_psnr=cov_psnr,
                cov_ssim=cov_ssim,
                sec_psnr=sec_psnr,
                sec_ssim=sec_ssim,
                inference_time=inference_time,  # ADD THIS
            )
            st.session_state.steg_result = (stego, rec, m)

    # Build results dict from session_state (persists until buttons are clicked again)
    results = {}
    metrics_all = {"LSB": None, "StegFormer": None}

    if st.session_state.lsb_result is not None:
        stego, rec, m = st.session_state.lsb_result
        results["LSB"] = (stego, rec, m)
        metrics_all["LSB"] = m

    if st.session_state.steg_result is not None:
        stego, rec, m = st.session_state.steg_result
        results["StegFormer"] = (stego, rec, m)
        metrics_all["StegFormer"] = m

    if not results:
        return

    # ---------- 3. Visual outputs (Originals + per‑algo tabs) ----------
    st.markdown("---")
    st.subheader("3. Visual outputs")

    algo_names = list(results.keys())
    tab_labels = ["Originals"] + algo_names
    tabs = st.tabs(tab_labels)

    # Originals tab
    with tabs[0]:
        o1, o2 = st.columns(2, gap="small")
        with o1:
            st.image(
                cover_pil,
                caption="Original Cover (256×256)",
                width=DISPLAY_WIDTH,
            )
        with o2:
            st.image(
                secret_pil,
                caption="Original Secret (256×256)",
                width=DISPLAY_WIDTH,
            )

    # Algorithm tabs
    for tab, name in zip(tabs[1:], algo_names):
        stego_np, rec_np, m = results[name]
        with tab:
            col1, col2 = st.columns(2, gap="small")
            with col1:
                st.image(
                    numpy_to_pil(stego_np),
                    caption=f"{name} Stego",
                    width=DISPLAY_WIDTH,
                )
            with col2:
                st.image(
                    numpy_to_pil(rec_np),
                    caption=f"{name} Recovered Secret",
                    width=DISPLAY_WIDTH,
                )

            st.markdown(
                f"**Cover → Stego**  \n"
                f"- PSNR: `{m['cov_psnr']:.2f}` dB  \n"
                f"- SSIM: `{m['cov_ssim']:.3f}`"
            )
            st.markdown(
                f"**Secret → Recovered**  \n"
                f"- PSNR: `{m['sec_psnr']:.2f}` dB  \n"
                f"- SSIM: `{m['sec_ssim']:.3f}`"
            )
            st.markdown(  # ADD THIS
                f"**Inference Time:** `{m['inference_time']:.1f}` ms"
            )

    # ---------- 4. Metrics comparison ----------
    st.markdown("---")
    st.subheader("4. Metrics comparison")

    table_rows = []
    for name, m in metrics_all.items():
        if m is None:
            continue
        table_rows.append(  # ADD INFERENCE TIME COLUMN
            {
                "Algorithm": name,
                "Cover PSNR": f"{m['cov_psnr']:.2f}",
                "Cover SSIM": f"{m['cov_ssim']:.3f}",
                "Secret PSNR": f"{m['sec_psnr']:.2f}",
                "Secret SSIM": f"{m['sec_ssim']:.3f}",
                "Inference (ms)": f"{m['inference_time']:.1f}",
            }
        )
    st.table(table_rows)

    # ---------- 5. Export as ZIP ----------
    st.markdown("---")
    st.subheader("5. Export results")

    zip_buf = build_zip(cover_np, secret_np, results, metrics_all)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="Download all images + metrics as ZIP",
        data=zip_buf.getvalue(),
        file_name=f"stego_results_{ts}.zip",
        mime="application/zip",
    )

if __name__ == "__main__":
    main()
