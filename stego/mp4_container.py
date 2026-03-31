import struct
from stego.utils import bytes_to_bits, bits_to_bytes

def find_mdat_block(data: bytes) -> tuple:
    pos = 0
    while pos < len(data) - 8:
        box_size = int.from_bytes(data[pos:pos + 4], 'big')
        box_type = data[pos + 4:pos + 8]
        if box_type == b'mdat' and box_size > 8:
            return pos + 8, box_size - 8
        if box_size == 0 or box_size < 8:
            break
        pos += box_size
    raise ValueError("No suitable mdat block found in this MP4 file")


def _get_workspace(content_start: int, content_size: int) -> tuple:
    third = content_size // 3
    return content_start + third, content_start + 2 * third


def get_capacity(mp4_path: str) -> int:
    with open(mp4_path, 'rb') as f:
        data = f.read()
    content_start, content_size = find_mdat_block(data)
    ws_start, ws_end = _get_workspace(content_start, content_size)
    return max(0, (ws_end - ws_start) // 8 - 14)


def _parity_encode(workspace: bytearray, offset: int, bits: list) -> None:
    for i, bit in enumerate(bits):
        b = workspace[offset + i]
        if b % 2 != bit:
            workspace[offset + i] = b + 1 if b < 0xFF else b - 1


def _parity_decode(data: bytes, offset: int, n_bits: int) -> list:
    return [data[offset + i] % 2 for i in range(n_bits)]


def _build_embed_data(payload: bytes, is_file: bool, filename: str,
                      is_encrypted: bool, is_random: bool) -> bytes:
    fname_bytes = filename.encode('utf-8') if filename else b''
    flags = (0x01 if is_file else 0) | (0x02 if is_encrypted else 0) | (0x04 if is_random else 0)

    inner = struct.pack('>BB', flags, 0x32)
    inner += struct.pack('>IH', len(payload), len(fname_bytes))
    inner += fname_bytes + payload

    total_size = 2 + 4 + len(inner)
    return struct.pack('>H', total_size) + b'STEG' + inner


def embed_mp4(src_path: str, out_path: str, payload: bytes,
              is_file: bool, filename: str,
              is_encrypted: bool, is_random: bool) -> None:
    with open(src_path, 'rb') as f:
        data = bytearray(f.read())

    content_start, content_size = find_mdat_block(bytes(data))
    ws_start, ws_end = _get_workspace(content_start, content_size)
    workspace_size = ws_end - ws_start

    bits = bytes_to_bits(_build_embed_data(payload, is_file, filename, is_encrypted, is_random))

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
    ws_start, ws_end = _get_workspace(content_start, content_size)
    workspace_size = ws_end - ws_start

    if workspace_size < 16:
        raise ValueError("mdat workspace too small to contain stego header")

    total_size = struct.unpack('>H', bits_to_bytes(_parity_decode(data, ws_start, 16)))[0]

    if total_size < 14 or total_size * 8 > workspace_size:
        raise ValueError("Failed to parse stego header: wrong key or not a stego video")

    all_bytes = bits_to_bytes(_parity_decode(data, ws_start, total_size * 8))

    if all_bytes[2:6] != b'STEG':
        raise ValueError("Failed to parse stego header: wrong key or not a stego video")

    pos = 6
    flags = all_bytes[pos]; pos += 1
    pos += 1 
    payload_len = struct.unpack('>I', all_bytes[pos:pos + 4])[0]; pos += 4
    fname_len = struct.unpack('>H', all_bytes[pos:pos + 2])[0]; pos += 2
    filename = all_bytes[pos:pos + fname_len].decode('utf-8', errors='replace'); pos += fname_len
    payload = all_bytes[pos:pos + payload_len]

    return payload, bool(flags & 0x01), filename, bool(flags & 0x02)