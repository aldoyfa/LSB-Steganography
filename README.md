# LSB Steganography on AVI & MP4

A Python desktop application to hide secret messages within video files using LSB (Least Significant Bit) steganography, with optional A5/1 stream cipher encryption.

## Tech Stack & Dependencies

- Python 3.x
- OpenCV (video I/O)
- NumPy (array/math operations)
- matplotlib (histogram visualization)
- tkinter (GUI framework)

## Features

- **Embedding & Extraction** of text messages and files into/from AVI and MP4 videos.
- **Two Embedding Methods**: Pixel-level LSB for AVI files and container-level metadata parity encoding for MP4 files (zero visual degradation).
- **3 LSB Schemes (AVI only)**: 3-3-2, 4-2-2, 2-3-3 (R-G-B bit distribution).
- **Optional A5/1 Encryption**: Stream cipher with configurable keys.
- **Sequential or Random Insertion (AVI only)**: Uses a stego-key as a seed for randomized pixel selection.
- **Quality Metrics**: MSE and PSNR calculated per-frame and as an average (MP4 always shows MSE 0.0, PSNR ∞).
- **Data Integrity Check**: SHA-256 hashing to verify extracted payload integrity.
- **Histogram Comparison**: Visual comparison between cover and stego videos.
- **Capacity Check**: Verification of message size before embedding.
- **Supported File Types**: .txt, .pdf, .docx, .png, .jpg, .exe, etc.

## Installation

```bash
pip install -r requirements.txt
```

## How to Run

```bash
python main.py
```

## Supported Formats

| Format | Notes |
|--------|---------|
| AVI | Pixel-level LSB. Lossless using FFV1 codec. |
| MP4 | Container-level parity encoding (modifies `mdat` box). 100% video/audio preservation, zero frame re-encoding. |

## Project Structure

```
├── main.py                  # Entry point
├── gui/
│   ├── app.py               # Main tkinter window
│   ├── embed_tab.py         # Embedding tab
│   ├── extract_tab.py       # Extraction tab
│   └── histogram_window.py  # Histogram popup
├── stego/
│   ├── a51.py               # A5/1 stream cipher
│   ├── lsb.py               # LSB embed/extract logic (AVI dispatch)
│   ├── mp4_container.py     # MP4 container parity logic
│   └── utils.py             # Helper functions & SHA-256
├── test_files/              # Test files folder
├── generate_test_video.py   # Test video generator
├── requirements.txt
└── README.md
```

## Notes

- Lossless pixel LSB is only guaranteed for AVI files using a lossless codec (FFV1).
- MP4 files use container-level embedding, which survives playback perfectly but will be lost if the video is uploaded to a platform that re-encodes (like YouTube or Twitter).
- Encryption keys and stego-keys are NOT stored inside the video file.

## References

- Container-level MP4 video steganography (`mdat` parity encoding) is based on the methodology from [JavDomGom/videostego](https://github.com/JavDomGom/videostego).