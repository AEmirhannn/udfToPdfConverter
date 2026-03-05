# UDF to PDF Converter

Convert `.udf` files into PDF documents using Python and ReportLab.

## Features

- Supports UDF files stored as:
  - raw XML files
  - ZIP-based archives containing `content.xml`
- Preserves basic formatting:
  - bold, italic, underline
  - paragraph alignment (left, center, right, justify)
  - line spacing
  - page breaks
- Uses available system Unicode fonts when generating PDFs

## Requirements

- Python 3.9+
- `reportlab`

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Usage

Convert one or more files:

```bash
python3 converter.py input1.udf [input2.udf ...]
```

Output files are created next to the source file, with the `_light.pdf` suffix.

Example:

- Input: `document.udf`
- Output: `document_light.pdf`

## Font Notes

The script searches for fonts in these locations:

- project root
- `fonts/` directory in the project
- `~/Library/Fonts`
- `/Library/Fonts`
- `/System/Library/Fonts/Supplemental`
- `/System/Library/Fonts`

Recommended fonts (any one regular variant is required):

- Noto Serif
- DejaVu Serif
- Times New Roman
- Arial

If no supported Unicode TTF font is found, conversion fails with an explicit error.

## Known Scope

This is a lightweight converter and does not implement every possible UDF feature. It focuses on reliable conversion of core text content and formatting.
