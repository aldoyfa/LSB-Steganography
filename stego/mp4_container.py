def find_mdat_block(data: bytes) -> tuple:
    pos = 0
    while pos < len(data) - 8:
        box_size = int.from_bytes(data[pos:pos + 4], 'big')
        box_type = data[pos + 4:pos + 8]
        if box_type == b'mdat' and box_size > 8:
            content_start = pos + 8
            content_size = box_size - 8
            return content_start, content_size
        if box_size == 0 or box_size < 8:
            break
        pos += box_size
    raise ValueError("No suitable mdat block found in this MP4 file")

def get_workspace(content_start: int, content_size: int) -> tuple:
    third = content_size // 3
    ws_start = content_start + third
    ws_end = content_start + 2 * third
    return ws_start, ws_end

def get_capacity(mp4_path: str) -> int:
    with open(mp4_path, 'rb') as f:
        data = f.read()
    content_start, content_size = find_mdat_block(data)
    ws_start, ws_end = get_workspace(content_start, content_size)
    workspace_bytes = ws_end - ws_start
    usable = (workspace_bytes // 8) - 14
    return max(0, usable)

def _parity_encode(workspace: bytearray, offset: int, bits: list) -> int:
    for i, bit in enumerate(bits):
        b = workspace[offset + i]
        if b % 2 != bit:
            workspace[offset + i] = b + 1 if b < 0xFF else b - 1
    return len(bits)

def _parity_decode(data: bytes, offset: int, n_bits: int) -> list:
    return [data[offset + i] % 2 for i in range(n_bits)]

def _build_embed_data(payload: bytes, is_file: bool, filename: str,
                      is_encrypted: bool, is_random: bool) -> bytes:

    fname_bytes = filename.encode('utf-8') if filename else b''

    flags = 0
    if is_file:       flags |= 0x01
    if is_encrypted:  flags |= 0x02
    if is_random:     flags |= 0x04

    inner = bytes([flags, 0x32])                        # flags, lsb_scheme
    inner += len(payload).to_bytes(4, 'big')            # payload_len
    inner += len(fname_bytes).to_bytes(2, 'big')        # fname_len
    inner += fname_bytes                                 # filename
    inner += payload                                     # payload

    total_size = 2 + 4 + len(inner)
    header = total_size.to_bytes(2, 'big') + b'STEG'

    return header + inner

def embed_mp4(src_path: str, out_path: str, payload: bytes,
              is_file: bool, filename: str,
              is_encrypted: bool, is_random: bool) -> None:
 
    with open(src_path, 'rb') as f:
        data = bytearray(f.read())

    content_start, content_size = find_mdat_block(bytes(data))
    ws_start, ws_end = get_workspace(content_start, content_size)
    workspace_size = ws_end - ws_start

    embed_data = _build_embed_data(payload, is_file, filename,
                                   is_encrypted, is_random)
    bits = _bits_from_bytes(embed_data)

    if len(bits) > workspace_size:
        raise ValueError(
            f"Payload too large: need {len(bits)} workspace bytes, "
            f"have {workspace_size} (max payload ≈ {(workspace_size // 8) - 14:,} bytes)"
        )

    _parity_encode(data, ws_start, bits)

    with open(out_path, 'wb') as f:
        f.write(data)

def extract_mp4(stego_path: str) -> tuple:
    with open(stego_path, 'rb') as f:
        data = f.read()

    content_start, content_size = find_mdat_block(data)
    ws_start, ws_end = get_workspace(content_start, content_size)
    workspace_size = ws_end - ws_start

    if workspace_size < 16:
        raise ValueError("mdat workspace too small to contain stego header")

    size_bits = _parity_decode(data, ws_start, 16)
    total_size = int.from_bytes(_bytes_from_bits(size_bits), 'big')

    if total_size < 14 or total_size * 8 > workspace_size:
        raise ValueError("Failed to parse stego header: wrong key or not a stego video")

    all_bits = _parity_decode(data, ws_start, total_size * 8)
    all_bytes = _bytes_from_bits(all_bits)

    magic = all_bytes[2:6]
    if magic != b'STEG':
        raise ValueError("Failed to parse stego header: wrong key or not a stego video")

    pos = 6
    flags      = all_bytes[pos];                        pos += 1
    _scheme    = all_bytes[pos];                        pos += 1   # ignored for MP4
    payload_len = int.from_bytes(all_bytes[pos:pos+4], 'big'); pos += 4
    fname_len   = int.from_bytes(all_bytes[pos:pos+2], 'big'); pos += 2
    filename    = all_bytes[pos:pos+fname_len].decode('utf-8', errors='replace')
    pos += fname_len
    payload     = all_bytes[pos:pos+payload_len]

    is_file      = bool(flags & 0x01)
    is_encrypted = bool(flags & 0x02)

    return payload, is_file, filename, is_encrypted