import cv2
import numpy as np
import random as _random
import os

from stego.utils import (bytes_to_bits, bits_to_bytes, parse_scheme,
                          pack_header, unpack_header_from_bits, calc_mse_psnr)
from stego.a51 import encrypt as a51_encrypt, decrypt as a51_decrypt

def get_capacity(video_path, scheme="3-3-2"):
    if _detect_format(video_path) == 'mp4':
        from stego.mp4_container import get_capacity as _mp4_cap
        return _mp4_cap(video_path)

    r_bits, g_bits, b_bits = parse_scheme(scheme)
    bpp = r_bits + g_bits + b_bits

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Can't open video: {video_path}")

    total_pixels = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        total_pixels += w * h
    cap.release()

    total_bits = total_pixels * bpp
    return total_bits // 8


def _get_pixel_order(w, h, use_random, stego_key, frame_idx):
    n_pixels = w * h
    indices = list(range(n_pixels))
    if use_random and stego_key:
        rng = _random.Random(f"{stego_key}_{frame_idx}")
        rng.shuffle(indices)
    return indices


def _embed_bits_in_frame(frame, bits, offset, scheme, use_random, stego_key, frame_idx):
    r_bits, g_bits, b_bits = parse_scheme(scheme)
    bpp = r_bits + g_bits + b_bits
    h, w = frame.shape[:2]
    order = _get_pixel_order(w, h, use_random, stego_key, frame_idx)

    stego = frame.copy()
    idx = offset
    for px_i in order:
        if idx >= len(bits):
            break
        y = px_i // w
        x = px_i % w
        pixel = list(stego[y, x])

        channel_bits = [(2, r_bits), (1, g_bits), (0, b_bits)]
        for ch, n in channel_bits:
            if n == 0 or idx >= len(bits):
                continue
            mask = (0xFF << n) & 0xFF
            val = pixel[ch] & mask
            for bit_pos in range(n - 1, -1, -1):
                if idx < len(bits):
                    val |= (bits[idx] << bit_pos)
                    idx += 1
            pixel[ch] = val

        stego[y, x] = pixel

    return stego, idx


def _extract_bits_from_frame(frame, n_bits, scheme, use_random, stego_key, frame_idx):
    r_bits, g_bits, b_bits = parse_scheme(scheme)
    h, w = frame.shape[:2]
    order = _get_pixel_order(w, h, use_random, stego_key, frame_idx)

    extracted = []
    count = 0
    for px_i in order:
        if count >= n_bits:
            break
        y = px_i // w
        x = px_i % w
        pixel = frame[y, x]

        channel_bits = [(2, r_bits), (1, g_bits), (0, b_bits)]
        for ch, n in channel_bits:
            if n == 0:
                continue
            for bit_pos in range(n - 1, -1, -1):
                if count < n_bits:
                    extracted.append((pixel[ch] >> bit_pos) & 1)
                    count += 1

    return extracted


def _detect_format(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.mp4':
        return 'mp4'
    return 'avi'


def _get_writer(out_path, fps, w, h):
    fmt = _detect_format(out_path)
    if fmt == 'mp4':
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    else:
        fourcc = cv2.VideoWriter_fourcc(*'FFV1')
    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
    if not writer.isOpened() and fmt == 'avi':
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
    return writer


def embed(video_path, out_path, payload_bytes, scheme, is_file, filename,
          use_encryption, key, use_random, stego_key, progress_cb=None):

    if _detect_format(video_path) == 'mp4':
        from stego.mp4_container import embed_mp4

        if use_encryption and key:
            enc_payload = a51_encrypt(payload_bytes, key)
        else:
            enc_payload = payload_bytes
            use_encryption = False

        if progress_cb:
            progress_cb(0, 1)
        embed_mp4(video_path, out_path, enc_payload,
                  is_file, filename if is_file else "",
                  use_encryption, use_random)
        if progress_cb:
            progress_cb(1, 1)
        return 0.0, float('inf'), [], []

    if use_encryption and key:
        enc_payload = a51_encrypt(payload_bytes, key)
    else:
        enc_payload = payload_bytes
        use_encryption = False

    header = pack_header(is_file, use_encryption, use_random, scheme,
                         len(enc_payload), filename if is_file else "")
    full_data = header + enc_payload
    all_bits = bytes_to_bits(full_data)

    cap_bytes = get_capacity(video_path, scheme)
    needed_bytes = len(full_data)
    if needed_bytes > cap_bytes:
        raise ValueError(f"Payload too large! Need {needed_bytes} bytes but capacity is {cap_bytes} bytes")

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    writer = _get_writer(out_path, fps, w, h)

    mse_vals = []
    psnr_vals = []
    bit_idx = 0
    frame_num = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if bit_idx < len(all_bits):
            stego_frame, bit_idx = _embed_bits_in_frame(
                frame, all_bits, bit_idx, scheme, use_random, stego_key, frame_num)
            mse, psnr = calc_mse_psnr(frame, stego_frame)
            mse_vals.append(mse)
            psnr_vals.append(psnr)
            writer.write(stego_frame)
        else:
            writer.write(frame)

        frame_num += 1
        if progress_cb:
            progress_cb(frame_num, total_frames)

    cap.release()
    writer.release()

    avg_mse = np.mean(mse_vals) if mse_vals else 0
    avg_psnr = np.mean([p for p in psnr_vals if p != float('inf')]) if psnr_vals else float('inf')

    return avg_mse, avg_psnr, mse_vals, psnr_vals


def extract(stego_path, a51_key=None, stego_key=None):
    if _detect_format(stego_path) == 'mp4':
        from stego.mp4_container import extract_mp4
        payload, is_file, filename, is_encrypted = extract_mp4(stego_path)
        if is_encrypted:
            if not a51_key:
                raise ValueError("Payload is encrypted but no A5/1 key provided")
            payload = a51_decrypt(payload, a51_key)
        return payload, is_file, filename

    cap = cv2.VideoCapture(stego_path)
    if not cap.isOpened():
        raise IOError(f"Can't open stego video: {stego_path}")

    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()

    if not frames:
        raise ValueError("No frames in stego video")

    SCHEMES = ["3-3-2", "4-2-2", "2-3-3"]
    header_info = None
    PROBE_BITS = 2048

    for try_scheme in SCHEMES:
        try:
            hdr_bits = _extract_bits_from_frame(
                frames[0], PROBE_BITS, try_scheme, False, None, 0)
            info = unpack_header_from_bits(hdr_bits)
            if info['scheme'] == try_scheme:
                header_info = info
                break
        except:
            continue

    if header_info is None and stego_key:
        for try_scheme in SCHEMES:
            try:
                hdr_bits = _extract_bits_from_frame(
                    frames[0], PROBE_BITS, try_scheme, True, stego_key, 0)
                info = unpack_header_from_bits(hdr_bits)
                if info['scheme'] == try_scheme:
                    header_info = info
                    break
            except:
                continue

    if header_info is None:
        raise ValueError("Failed to parse stego header: wrong key or not a stego video")

    use_random = header_info['is_random']
    scheme = header_info['scheme']
    payload_len = header_info['payload_len']
    total_bits_needed = header_info['header_bits'] + payload_len * 8

    all_extracted = []
    bits_remaining = total_bits_needed
    for fi, frame in enumerate(frames):
        if bits_remaining <= 0:
            break
        r_bits, g_bits, b_bits = parse_scheme(scheme)
        bpp = r_bits + g_bits + b_bits
        frame_capacity = frame.shape[0] * frame.shape[1] * bpp
        n = min(bits_remaining, frame_capacity)
        frame_bits = _extract_bits_from_frame(
            frame, n, scheme, use_random, stego_key if use_random else None, fi)
        all_extracted.extend(frame_bits)
        bits_remaining -= len(frame_bits)

    hdr = unpack_header_from_bits(all_extracted)
    payload_start = hdr['header_bits']
    payload_bits = all_extracted[payload_start:payload_start + payload_len * 8]
    payload_raw = bits_to_bytes(payload_bits)[:payload_len]

    if hdr['is_encrypted']:
        if not a51_key:
            raise ValueError("Payload is encrypted but no A5/1 key provided")
        payload_raw = a51_decrypt(payload_raw, a51_key)

    return payload_raw, hdr['is_file'], hdr['filename']