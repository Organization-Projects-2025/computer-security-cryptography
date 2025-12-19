# batch_stego_benchmark.py - FULL VERSION WITH SAMPLE OPTIONS
import os
import time
import glob
import argparse
import numpy as np
from pathlib import Path
from PIL import Image
import pandas as pd

from utils.image_io import pil_to_numpy, numpy_to_pil
from utils.metrics import compute_psnr, compute_ssim
from lsb.lsb_stego import lsb_hide, lsb_reveal
from stegformer_infer import StegFormerInfer

STEGO_SIZE = (256, 256)

def load_stegformer(weights_path: str):
    return StegFormerInfer(weights_path)

def resize_256(img: Image.Image) -> Image.Image:
    return img.resize(STEGO_SIZE, Image.BICUBIC)

def process_single_pair(cover_path, secret_path, stegformer):
    """Process one cover-secret pair"""
    try:
        cover_pil = resize_256(Image.open(cover_path).convert("RGB"))
        secret_pil = resize_256(Image.open(secret_path).convert("RGB"))
        cover_np = pil_to_numpy(cover_pil)
        secret_np = pil_to_numpy(secret_pil)
        
        results = []
        
        # LSB
        start_time = time.time()
        stego_lsb = lsb_hide(cover_np, secret_np)
        rec_lsb = lsb_reveal(stego_lsb)
        lsb_time = (time.time() - start_time) * 1000
        
        results.append({
            'algo': 'LSB',
            'filename': Path(cover_path).stem,
            'pair_id': len(results),
            'cov_psnr': compute_psnr(cover_np, stego_lsb),
            'cov_ssim': compute_ssim(cover_np, stego_lsb),
            'sec_psnr': compute_psnr(secret_np, rec_lsb),
            'sec_ssim': compute_ssim(secret_np, rec_lsb),
            'inference_time': lsb_time
        })
        
        # StegFormer
        start_time = time.time()
        stego_sf = stegformer.hide(cover_np, secret_np)
        rec_sf = stegformer.reveal(stego_sf)
        sf_time = (time.time() - start_time) * 1000
        
        results.append({
            'algo': 'StegFormer',
            'filename': Path(cover_path).stem,
            'pair_id': len(results),
            'cov_psnr': compute_psnr(cover_np, stego_sf),
            'cov_ssim': compute_ssim(cover_np, stego_sf),
            'sec_psnr': compute_psnr(secret_np, rec_sf),
            'sec_ssim': compute_ssim(secret_np, rec_sf),
            'inference_time': sf_time
        })
        
        return results
        
    except Exception as e:
        print(f"Error processing {cover_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Batch steganography benchmark")
    parser.add_argument('--covers', default="dataset/covers/", help="Cover images folder")
    parser.add_argument('--secrets', default="dataset/secrets/", help="Secret images folder")
    parser.add_argument('--weights', default="weights/StegFormer-S_baseline.pt", help="StegFormer weights")
    parser.add_argument('--sample', type=int, help="Process only first N pairs (e.g. --sample 50)")
    parser.add_argument('--output', default="batch_results.csv", help="Output CSV name")
    
    args = parser.parse_args()
    
    # Verify folders
    if not os.path.exists(args.covers):
        print(f"❌ Cover folder not found: {args.covers}")
        return
    if not os.path.exists(args.secrets):
        print(f"❌ Secret folder not found: {args.secrets}")
        return
    
    # Load model
    print("Loading StegFormer...")
    stegformer = load_stegformer(args.weights)
    print("✅ StegFormer loaded")
    
    # Get image files
    cover_files = sorted(glob.glob(os.path.join(args.covers, "*.png")) + 
                        glob.glob(os.path.join(args.covers, "*.jpg")) +
                        glob.glob(os.path.join(args.covers, "*.jpeg")))
    secret_files = sorted(glob.glob(os.path.join(args.secrets, "*.png")) + 
                         glob.glob(os.path.join(args.secrets, "*.jpg")) +
                         glob.glob(os.path.join(args.secrets, "*.jpeg")))
    
    print(f"Found {len(cover_files)} cover images")
    print(f"Found {len(secret_files)} secret images")
    
    min_pairs = min(len(cover_files), len(secret_files))
    if args.sample:
        min_pairs = min(min_pairs, args.sample)
        print(f"Using sample size: {min_pairs}")
    
    print(f"Processing {min_pairs} image pairs...")
    
    # Process
    all_results = []
    successful_pairs = 0
    
    for i in range(min_pairs):
        cover_path = cover_files[i]
        secret_path = secret_files[i]
        
        if i % 50 == 0 or i < 5:
            print(f"Progress: {i+1}/{min_pairs} ({100*(i+1)/min_pairs:.1f}%)")
        
        metrics_pair = process_single_pair(cover_path, secret_path, stegformer)
        if metrics_pair:
            all_results.extend(metrics_pair)
            successful_pairs += 1
    
    print(f"\n✅ Completed {successful_pairs}/{min_pairs} pairs successfully")
    
    # Save detailed results
    df_detailed = pd.DataFrame(all_results)
    df_detailed.to_csv(args.output, index=False)
    print(f"Detailed results saved: {args.output}")
    
    # Summary
    print("\n" + "="*70)
    print("BATCH RESULTS (AVERAGES)")
    print("="*70)
    
    summary = {}
    for algo in ['LSB', 'StegFormer']:
        algo_data = df_detailed[df_detailed['algo'] == algo]
        
        if len(algo_data) == 0:
            continue
            
        avg_metrics = {
            'cov_psnr': algo_data['cov_psnr'].mean(),
            'cov_psnr_std': algo_data['cov_psnr'].std(),
            'cov_ssim': algo_data['cov_ssim'].mean(),
            'cov_ssim_std': algo_data['cov_ssim'].std(),
            'sec_psnr': algo_data['sec_psnr'].mean(),
            'sec_psnr_std': algo_data['sec_psnr'].std(),
            'sec_ssim': algo_data['sec_ssim'].mean(),
            'sec_ssim_std': algo_data['sec_ssim'].std(),
            'inference_time': algo_data['inference_time'].mean(),
            'inference_time_std': algo_data['inference_time'].std(),
            'n_samples': len(algo_data)
        }
        summary[algo] = avg_metrics
        
        print(f"\n{algo}:")
        print(f"  Cover PSNR:   {avg_metrics['cov_psnr']:.1f} ± {avg_metrics['cov_psnr_std']:.1f} dB")
        print(f"  Cover SSIM:   {avg_metrics['cov_ssim']:.3f} ± {avg_metrics['cov_ssim_std']:.3f}")
        print(f"  Secret PSNR:  {avg_metrics['sec_psnr']:.1f} ± {avg_metrics['sec_psnr_std']:.1f} dB")
        print(f"  Secret SSIM:  {avg_metrics['sec_ssim']:.3f} ± {avg_metrics['sec_ssim_std']:.3f}")
        print(f"  Inference:    {avg_metrics['inference_time']:.0f} ± {avg_metrics['inference_time_std']:.0f} ms")
        print(f"  Samples:      {avg_metrics['n_samples']}")
    
    summary_df = pd.DataFrame(summary).T
    summary_df.to_csv("summary_averages.csv")
    print(f"\nSummary saved: summary_averages.csv")
    print("\n✅ Batch complete!")

if __name__ == "__main__":
    main()
