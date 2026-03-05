# UDF to PDF Converter

Convert `.udf` files into PDF documents using Python and ReportLab.

## Features

- Accepts UDF input as:
  - raw XML `.udf`
  - ZIP-based `.udf` archives containing `content.xml`
- Preserves core formatting:
  - bold, italic, underline
  - paragraph alignment (left, center, right, justify)
  - line spacing
  - page breaks
- Cross-platform font discovery for macOS, Linux, and Windows
- Supports custom font directory via `UDF_FONT_DIR`

## Requirements

- Python 3.9+
- `reportlab`

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Windows PowerShell equivalent:

```powershell
py -m pip install -r requirements.txt
```

## Usage

Convert one or more files:

```bash
python3 converter.py input1.udf [input2.udf ...]
```

Windows PowerShell equivalent:

```powershell
py converter.py input1.udf input2.udf
```

Output files are created next to each source file with `_light.pdf` suffix.

Example:

- Input: `document.udf`
- Output: `document_light.pdf`

## Font Setup

The converter searches for font files in this order:

1. `UDF_FONT_DIR` (if set)
2. `fonts/` in this repository
3. project root
4. platform font directories:
   - macOS: `~/Library/Fonts`, `/Library/Fonts`, `/System/Library/Fonts/...`
   - Linux: `~/.local/share/fonts`, `~/.fonts`, `/usr/local/share/fonts`, `/usr/share/fonts`
   - Windows: `%WINDIR%\\Fonts`

Recommended font family for consistent output: Noto Serif (`Regular`, `Bold`, `Italic`, `BoldItalic`).

If no supported regular TTF font is found, the script exits with an explicit error describing searched locations.

## Repository Hygiene

- `.udf` files are gitignored by default to prevent publishing user/sample data.
- Generated PDFs are gitignored.

## Scope

This is a lightweight converter and does not implement every possible UDF feature. It is focused on reliable conversion of core text content and formatting.
