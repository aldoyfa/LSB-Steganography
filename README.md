# LSB Steganography on AVI & MP4

A Python desktop application to hide secret messages within video files using LSB (Least Significant Bit) steganography, with optional A5/1 stream cipher encryption.

## Tech Stack

- Python 3.x
- OpenCV (video I/O)
- NumPy (array/math operations)
- matplotlib (histogram visualization)
- tkinter (GUI framework)

## Features

- **Embedding & Extraction** of text messages and files into/from AVI and MP4 videos.
- **3 LSB Schemes**: 3-3-2, 4-2-2, 2-3-3 (R-G-B bit distribution).
- **Optional A5/1 Encryption**: Stream cipher with configurable keys.
- **Sequential or Random Insertion**: Uses a stego-key as a seed for randomized pixel selection.
- **Quality Metrics**: MSE and PSNR calculated per-frame and as an average.
- **Histogram Comparison**: Visual comparison between cover and stego videos.
- **Capacity Check**: Verification of message size before embedding.
- **Supported File Types**: .txt, .pdf, .docx, .png, .jpg, .exe, etc.

## Installation

```bash
pip install -r requirements.txta
```

## How to Run

```bash
python main.py
```

## Supported Formats

| Format | Notes |
|--------|---------|
| AVI | Lossless using FFV1 codec |
| MP4 | Lossy — LSB bits may not be 100% preserved due to re-encoding |

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
│   ├── lsb.py               # LSB embed/extract logic
│   └── utils.py             # Helper functions
├── test_files/              # Test files folder
├── generate_test_video.py   # Test video generator
├── requirements.txt
└── README.md
```

## Notes

- Lossless LSB is only guaranteed for AVI files using a lossless codec (FFV1).
- MP4 uses lossy compression; there is a high probability that LSB bits will be altered during re-encoding, potentially making data extraction fail.
- Encryption keys and stego-keys are NOT stored inside the video file.