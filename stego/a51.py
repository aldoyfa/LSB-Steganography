BLOCK_BITS = 228

# LFSR sizes
R1_LEN = 19
R2_LEN = 22
R3_LEN = 23

# Feedback tap
R1_TAPS = [13, 16, 17, 18]
R2_TAPS = [20, 21]
R3_TAPS = [7, 20, 21, 22]

# Clock bit
R1_CLK = 8
R2_CLK = 10
R3_CLK = 10

def _get_bit(reg, pos):
    return (reg >> pos) & 1

def _clock_reg(reg, taps, length):
    feedback = 0
    for t in taps:
        feedback ^= _get_bit(reg, t)
    reg = (reg >> 1) | (feedback << (length - 1))
    return reg

def _majority(r1, r2, r3):
    b1 = _get_bit(r1, R1_CLK)
    b2 = _get_bit(r2, R2_CLK)
    b3 = _get_bit(r3, R3_CLK)
    return int(b1 + b2 + b3 >= 2)

def _clock_all_majority(r1, r2, r3):
    maj = _majority(r1, r2, r3)
    if _get_bit(r1, R1_CLK) == maj:
        r1 = _clock_reg(r1, R1_TAPS, R1_LEN)
    if _get_bit(r2, R2_CLK) == maj:
        r2 = _clock_reg(r2, R2_TAPS, R2_LEN)
    if _get_bit(r3, R3_CLK) == maj:
        r3 = _clock_reg(r3, R3_TAPS, R3_LEN)
    return r1, r2, r3


def _init_registers(kc_bits, fn_bits):
    r1 = r2 = r3 = 0

    # load key (64 bits)
    for i in range(64):
        r1 = _clock_reg(r1, R1_TAPS, R1_LEN)
        r2 = _clock_reg(r2, R2_TAPS, R2_LEN)
        r3 = _clock_reg(r3, R3_TAPS, R3_LEN)
        bit = kc_bits[i]
        r1 ^= bit
        r2 ^= bit
        r3 ^= bit

    # load frame number (22 bits)
    for i in range(22):
        r1 = _clock_reg(r1, R1_TAPS, R1_LEN)
        r2 = _clock_reg(r2, R2_TAPS, R2_LEN)
        r3 = _clock_reg(r3, R3_TAPS, R3_LEN)
        bit = fn_bits[i]
        r1 ^= bit
        r2 ^= bit
        r3 ^= bit

    for _ in range(100):
        r1, r2, r3 = _clock_all_majority(r1, r2, r3)

    return r1, r2, r3


def _generate_keystream(kc_bits, fn, n_bits):
    fn_bits = [(fn >> i) & 1 for i in range(22)]
    r1, r2, r3 = _init_registers(kc_bits, fn_bits)

    stream = []
    for _ in range(n_bits):
        r1, r2, r3 = _clock_all_majority(r1, r2, r3)
        out = _get_bit(r1, R1_LEN-1) ^ _get_bit(r2, R2_LEN-1) ^ _get_bit(r3, R3_LEN-1)
        stream.append(out)
    return stream


def _key_to_bits(key_str):
    raw = key_str.encode('utf-8')
    if len(raw) < 8:
        raw = raw + b'\x00' * (8 - len(raw))
    else:
        raw = raw[:8]
    bits = []
    for byte in raw:
        for i in range(8):
            bits.append((byte >> i) & 1)
    return bits


def encrypt(plaintext_bytes, key_str):
    kc_bits = _key_to_bits(key_str)
    plain_bits = []
    for b in plaintext_bytes:
        for i in range(8):
            plain_bits.append((b >> (7 - i)) & 1)

    cipher_bits = []
    fn = 0
    for offset in range(0, len(plain_bits), BLOCK_BITS):
        chunk = plain_bits[offset:offset + BLOCK_BITS]
        ks = _generate_keystream(kc_bits, fn, len(chunk))
        for j in range(len(chunk)):
            cipher_bits.append(chunk[j] ^ ks[j])
        fn += 1

    out = bytearray()
    for i in range(0, len(cipher_bits), 8):
        byte_bits = cipher_bits[i:i+8]
        if len(byte_bits) < 8:
            byte_bits += [0] * (8 - len(byte_bits))
        val = 0
        for bit in byte_bits:
            val = (val << 1) | bit
        out.append(val)
    return bytes(out)


def decrypt(ciphertext_bytes, key_str):
    return encrypt(ciphertext_bytes, key_str)