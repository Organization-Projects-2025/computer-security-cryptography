import numpy as np
from PIL import Image

def lsb_embed_text(cover_np, text_payload):
    """Embed TEXT payload using LSB - FIXED for uint8"""
    payload_bytes = text_payload.encode('utf-8')
    payload_bits = ''.join(format(b, '08b') for b in payload_bytes)
    payload_bits += '1111111111111111'  # End marker
    
    # ✅ CRITICAL FIX: Work with int32 to avoid overflow
    stego_flat = cover_np.flatten().astype(np.int32)  # Use int32 temporarily
    bit_idx = 0
    
    for i in range(len(stego_flat)):
        if bit_idx < len(payload_bits):
            # Clear LSB and set new bit
            stego_flat[i] = (stego_flat[i] & ~1) | int(payload_bits[bit_idx])
            bit_idx += 1
        else:
            break
    
    # ✅ Convert back to uint8 (clamps 0-255)
    return stego_flat.clip(0, 255).astype(np.uint8).reshape(cover_np.shape)

def lsb_extract_text(stego_np, max_chars=2000):
    """Extract TEXT payload until end marker"""
    stego_flat = stego_np.flatten()
    bits = ''
    
    for pixel in stego_flat:
        bits += str(pixel & 1)
        if len(bits) >= max_chars * 8 + 16:
            break
    
    end_marker = '1111111111111111'
    end_idx = bits.find(end_marker)
    if end_idx != -1:
        bits = bits[:end_idx]
    
    text = ''
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        if len(byte_bits) == 8:
            try:
                text += chr(int(byte_bits, 2))
            except:
                break
    
    return text.strip()
