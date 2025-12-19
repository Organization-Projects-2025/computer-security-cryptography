import streamlit as st
import numpy as np
from PIL import Image
import io
import logging

from lsb_stego import lsb_embed_text, lsb_extract_text
from hybrid_analyzer import HybridThreatAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="StegoThreat Simulator", layout="wide")

st.title("🦠 StegoThreat Simulator")

# Initialize analyzer
try:
    analyzer = HybridThreatAnalyzer()
    st.sidebar.success("✅ Analyzer initialized")
except Exception as e:
    st.error(f"❌ Analyzer init failed: {e}")
    st.stop()

st.sidebar.markdown("""
### 📋 Status
- YARA: ✅ Loaded
- VirusTotal v3: 🌐 Enabled (API key in code)
- LSB: ✅ Ready
""")

tab1, tab2 = st.tabs(["📤 Sender (Attacker)", "📥 Receiver (Security)"])

# ========== SENDER ==========
with tab1:
    st.header("Embed Payload in Image")

    col1, col2 = st.columns([1, 2])
    with col1:
        cover_image = st.file_uploader("Cover Image", type=["png", "jpg", "jpeg"])
    with col2:
        payload = st.text_area(
            "Malicious Payload (text)",
            value="""import socket
s = socket.socket()
s.connect(('127.0.0.1', 4444))
print("REVERSE SHELL CONNECTED!")""",
            height=200,
        )

    if st.button("🚀 SEND INFECTED IMAGE", type="primary") and cover_image and payload:
        try:
            logger.info("Starting embed process")
            image = Image.open(cover_image).convert("RGB")
            cover_np = np.array(image)

            stego_np = lsb_embed_text(cover_np, payload)
            stego_image = Image.fromarray(stego_np)

            stego_buffer = io.BytesIO()
            stego_image.save(stego_buffer, format="PNG")
            stego_buffer.seek(0)
            st.session_state.stego_data = stego_buffer.getvalue()

            col_a, col_b = st.columns(2)
            with col_a:
                st.image(image, caption="✅ Original", width=300)
            with col_b:
                st.image(stego_image, caption="🦠 Infected", width=300)

            st.download_button(
                "💾 Download infected.png",
                stego_buffer.getvalue(),
                "infected.png",
            )
            st.success(f"✅ {len(payload.encode())} bytes embedded")
            logger.info("Embed successful")

        except Exception as e:
            logger.error(f"Embed error: {e}")
            st.error(f"❌ Embed failed: {e}")

# ========== RECEIVER ==========
with tab2:
    st.header("Threat Analysis Pipeline")

    uploaded = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])

    if st.button("🔍 FULL ANALYSIS", type="primary") and uploaded:
        try:
            logger.info("Starting analysis")
            image = Image.open(uploaded).convert("RGB")
            extracted = lsb_extract_text(np.array(image))

            col1, col2 = st.columns(2)

            # Left side: image + payload
            with col1:
                st.subheader("📸 Image Analysis")
                st.success("✅ Clean (passes visual inspection)")
                st.subheader("🔍 Extracted Payload")
                st.code(extracted or "(no payload found)", language="python")

            # Right side: detections
            with col2:
                st.subheader("🛡️ Hybrid Detection")
                result = analyzer.analyze(extracted)
                vt = result.get("virustotal")

                st.metric("Overall Risk Score", f"{result['risk_score']}%")
                st.info(f"**Status:** {result['status']}")

                # YARA
                st.subheader("🎯 YARA Results")
                if result["yara"]["detected"]:
                    for threat in result["yara"]["threats"]:
                        st.error(f"🚨 {threat['rule']} (score: {threat['score']})")
                else:
                    st.success("✅ No YARA detections")

                # VirusTotal v3 (submit + link only)
                st.subheader("🌐 VirusTotal v3")

                if not vt or vt.get("error"):
                    msg = vt.get("error") if vt and "error" in vt else "Not available"
                    st.info(f"VirusTotal: {msg}")
                else:
                    sha256 = vt.get("sha256", "")
                    st.success("✅ Payload submitted to VirusTotal")
                    if sha256:
                        st.code(sha256, language="text")
                        st.markdown(
                            f"[Open in VirusTotal](https://www.virustotal.com/gui/file/{sha256})"
                        )
                    else:
                        st.info("SHA-256 not available")

            logger.info("Analysis complete")

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            st.error(f"❌ Analysis failed: {e}")
