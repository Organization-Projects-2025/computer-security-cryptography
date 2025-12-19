# StegoThreat Simulator & Stegano-Comparison READMEs

## 1. StegoThreat Simulator (app.py)

# 🦠 StegoThreat Simulator

**AV Pipeline Demo: LSB Steganography Detection** - Simulates how antivirus engines detect hidden payloads in images.

## 🎯 Features

- **Sender Tab**: Embed Python reverse shell payload via LSB steganography
- **Receiver Tab**: 3-stage AV pipeline (Static Scan → Stego Suspicion → Payload Extraction)
- **Realistic Detection**: YARA rules + VirusTotal v3 API integration

## 📊 Live Demo Results

Stage 2 Stego Suspicion: LSB heuristic (runs-length analysis)
Stage 3: Only triggers on Medium/High likelihood → lsb_extract_text → Hybrid analysis

## 🚀 Quick Start

# 1. Install

pip install streamlit pillow numpy lsb_stego hybrid_analyzer

# 2. Run

streamlit run app.py

## 🛠️ Architecture

Sender: Image → lsb_embed_text → Download infected.png
Receiver:
Stage 1: Visual inspection (always passes)
Stage 2: LSB runs analysis → Low/Med/High score
Stage 3: lsb_extract_text → YARA + VirusTotal

## 📈 Key Insight

**Real AVs don't blindly extract** - they use cheap statistical heuristics first, only running expensive steganalysis modules when suspicious.

## Dependencies

- streamlit, pillow, numpy
- lsb_stego (custom LSB embed/extract)
- hybrid_analyzer (YARA + VTv3)

---

**Educational demo showing AV triage logic in action.**

---

## 2. Stegano-Comparison (LSB vs StegFormer)

# 🔬 Stegano-Comparison: LSB vs StegFormer

**Streamlit GUI + Batch Benchmark** comparing classical LSB vs neural steganography across 500+ images.

## 📊 Benchmark Results (N=500)

| Metric          | LSB               | StegFormer        |
| --------------- | ----------------- | ----------------- |
| **Cover PSNR**  | 31.9 ± 0.7 dB     | **48.1 ± 3.5 dB** |
| **Cover SSIM**  | 0.919 ± 0.043     | **0.997 ± 0.003** |
| **Secret SSIM** | **0.910 ± 0.053** | 0.698 ± 0.105     |
| **Inference**   | **200 ± 11 ms**   | 406 ± 39 ms       |

**Key Finding:** StegFormer excels imperceptibility, LSB wins payload recovery.

## 🚀 Quick Start

### GUI (streamlit_app.py)

pip install streamlit torch torchvision pillow opencv-python scikit-image
streamlit run streamlit_app.py
**Features:** Upload cover/secret → Run LSB & StegFormer → Side-by-side metrics + ZIP export

### Batch Benchmark (batch_stego_benchmark.py)

# Test 50 images (2 min)

python batch_stego_benchmark.py --sample 50

# Full 500 images (90 min)

python batch_stego_benchmark.py --sample 500

## 📁 Folder Structure

stegano-comparison/
├── streamlit_app.py # GUI
├── batch_stego_benchmark.py # 500-image benchmark
├── weights/StegFormer-S_baseline.pt
├── dataset/
│ ├── covers/ # 500+ cover images
│ └── secrets/ # 500+ secret images
├── lsb/
├── utils/
└── outputs/
├── batch_results_500.csv
└── summary_averages.csv # Paper-ready!

## 🛠️ Key Components

GUI: Cover(256x256) + Secret → [LSB | StegFormer] → PSNR/SSIM + ZIP export
Batch: 500 pairs → CSV(2000 rows) → Averages ± STD for paper Table 1

## 📈 Usage Examples

# Quick test

python batch_stego_benchmark.py --sample 10

# Custom dataset

python batch_stego_benchmark.py --covers my_data/covers/ --sample 100

# Full paper benchmark

python batch_stego_benchmark.py --sample 500 --output paper_results.csv

## 🎓 Research Validation

- **N=500 diverse images** across domains
- **PSNR/SSIM** computed for cover→stego & secret→recovered
- **Inference time** measured (hide+reveal)
- **Reproducible** CSV exports for LaTeX tables

## Dependencies

torch, torchvision, streamlit, pillow, opencv-python, scikit-image, pandas, numpy

---

**Publication-ready steganography benchmark confirming StegFormer SOTA imperceptibility vs LSB recovery.**
