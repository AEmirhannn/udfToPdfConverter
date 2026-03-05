import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def is_zip_file(file_path):
    try:
        with zipfile.ZipFile(file_path, "r"):
            return True
    except zipfile.BadZipFile:
        return False


def load_udf_root(udf_file):
    if is_zip_file(udf_file):
        with zipfile.ZipFile(udf_file, "r") as z:
            if "content.xml" not in z.namelist():
                raise RuntimeError("'content.xml' not found in UDF archive")
            with z.open("content.xml") as content_file:
                tree = ET.parse(content_file, parser=ET.XMLParser(encoding="utf-8"))
                return tree.getroot()
    tree = ET.parse(udf_file, parser=ET.XMLParser(encoding="utf-8"))
    return tree.getroot()


def get_font_search_dirs():
    project_dir = Path(__file__).resolve().parent
    search_dirs = [project_dir / "fonts", project_dir]

    user_font_dir = os.getenv("UDF_FONT_DIR")
    if user_font_dir:
        search_dirs.insert(0, Path(user_font_dir).expanduser())

    if sys.platform.startswith("win"):
        windir = os.environ.get("WINDIR", r"C:\Windows")
        search_dirs.append(Path(windir) / "Fonts")
    elif sys.platform == "darwin":
        search_dirs.extend([
            Path("~/Library/Fonts").expanduser(),
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts/Supplemental"),
            Path("/System/Library/Fonts"),
        ])
    else:
        search_dirs.extend([
            Path("~/.local/share/fonts").expanduser(),
            Path("~/.fonts").expanduser(),
            Path("/usr/local/share/fonts"),
            Path("/usr/share/fonts"),
        ])

    unique_dirs = []
    seen = set()
    for directory in search_dirs:
        key = str(directory)
        if key not in seen:
            unique_dirs.append(directory)
            seen.add(key)
    return unique_dirs


def find_font_path(candidates):
    candidate_set = {name.lower() for name in candidates}

    for directory in get_font_search_dirs():
        if not directory.is_dir():
            continue

        for name in candidates:
            path = directory / name
            if path.is_file():
                return str(path)

        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.lower() in candidate_set:
                    return str(Path(root) / filename)
    return None


def configure_fonts():
    regular = find_font_path([
        "NotoSerif-Regular.ttf",
        "DejaVuSerif.ttf",
        "arial.ttf",
        "Times New Roman.ttf",
        "times.ttf",
        "LiberationSerif-Regular.ttf",
    ])
    bold = find_font_path([
        "NotoSerif-Bold.ttf",
        "DejaVuSerif-Bold.ttf",
        "arialbd.ttf",
        "Times New Roman Bold.ttf",
        "timesbd.ttf",
        "LiberationSerif-Bold.ttf",
    ])
    italic = find_font_path([
        "NotoSerif-Italic.ttf",
        "DejaVuSerif-Italic.ttf",
        "ariali.ttf",
        "Times New Roman Italic.ttf",
        "timesi.ttf",
        "LiberationSerif-Italic.ttf",
    ])
    bold_italic = find_font_path([
        "NotoSerif-BoldItalic.ttf",
        "DejaVuSerif-BoldItalic.ttf",
        "arialbi.ttf",
        "Times New Roman Bold Italic.ttf",
        "timesbi.ttf",
        "LiberationSerif-BoldItalic.ttf",
    ])

    if not regular:
        search_locations = "\n- ".join(str(p) for p in get_font_search_dirs())
        raise RuntimeError(
            "No supported TTF font found. Add Noto Serif or DejaVu Serif files to the 'fonts/' "
            f"folder or set UDF_FONT_DIR.\nSearched:\n- {search_locations}"
        )

    pdfmetrics.registerFont(TTFont("UDFBase", regular))

    font_variants = {
        "regular": "UDFBase",
        "bold": "UDFBase",
        "italic": "UDFBase",
        "boldItalic": "UDFBase",
    }

    if bold:
        pdfmetrics.registerFont(TTFont("UDFBase-Bold", bold))
        font_variants["bold"] = "UDFBase-Bold"
    if italic:
        pdfmetrics.registerFont(TTFont("UDFBase-Italic", italic))
        font_variants["italic"] = "UDFBase-Italic"
    if bold_italic:
        pdfmetrics.registerFont(TTFont("UDFBase-BoldItalic", bold_italic))
        font_variants["boldItalic"] = "UDFBase-BoldItalic"

    pdfmetrics.registerFontFamily(
        "UDFBase",
        normal=font_variants["regular"],
        bold=font_variants["bold"],
        italic=font_variants["italic"],
        boldItalic=font_variants["boldItalic"],
    )

    return font_variants


def alignment_from_udf(value):
    return {
        "1": TA_CENTER,
        "2": TA_RIGHT,
        "3": TA_JUSTIFY,
    }.get(str(value), TA_LEFT)


def line_spacing_to_leading(font_size, udf_line_spacing):
    try:
        udfls = float(udf_line_spacing)
    except (TypeError, ValueError):
        udfls = 0.2

    # UDF stores spacing as an offset-like value (e.g. 0.25 -> ~1.25x)
    multiplier = max(1.0, 1.0 + udfls)
    return font_size * multiplier


def markup_text(text, bold=False, italic=False, underline=False):
    s = escape(text)
    if bold:
        s = f"<b>{s}</b>"
    if italic:
        s = f"<i>{s}</i>"
    if underline:
        s = f"<u>{s}</u>"
    return s


def build_paragraph_text(para_elem, content_buffer):
    chunks = []
    for child in para_elem:
        if child.tag == "content":
            start = int(child.get("startOffset", "0"))
            length = int(child.get("length", "0"))
            text = content_buffer[start:start + length]
            chunks.append(
                markup_text(
                    text,
                    bold=child.get("bold", "false") == "true",
                    italic=child.get("italic", "false") == "true",
                    underline=child.get("underline", "false") == "true",
                )
            )
        elif child.tag == "field":
            if child.get("startOffset") and child.get("length"):
                start = int(child.get("startOffset", "0"))
                length = int(child.get("length", "0"))
                text = content_buffer[start:start + length]
            else:
                text = child.get("fieldName", "")
            chunks.append(
                markup_text(
                    text,
                    bold=child.get("bold", "false") == "true",
                    italic=child.get("italic", "false") == "true",
                    underline=child.get("underline", "false") == "true",
                )
            )
        elif child.tag == "space":
            chunks.append(" ")
    return "".join(chunks)


def udf_to_pdf_light(udf_file, pdf_file):
    root = load_udf_root(udf_file)
    font_variants = configure_fonts()

    content_elem = root.find("content")
    if content_elem is None or content_elem.text is None:
        raise RuntimeError("UDF content buffer not found")
    content_buffer = content_elem.text

    page_format = root.find("properties/pageFormat")
    left_margin = float(page_format.get("leftMargin", "42.5")) if page_format is not None else 42.5
    right_margin = float(page_format.get("rightMargin", "42.5")) if page_format is not None else 42.5
    top_margin = float(page_format.get("topMargin", "42.5")) if page_format is not None else 42.5
    bottom_margin = float(page_format.get("bottomMargin", "42.5")) if page_format is not None else 42.5

    elements = root.find("elements")
    if elements is None:
        raise RuntimeError("UDF elements section not found")

    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
    )

    stylesheet = getSampleStyleSheet()
    flow = []

    for elem in elements:
        if elem.tag == "paragraph":
            font_size = float(elem.get("size", "12"))
            style = ParagraphStyle(
                "UDFParagraph",
                parent=stylesheet["Normal"],
                alignment=alignment_from_udf(elem.get("Alignment", "0")),
                fontName=font_variants["regular"],
                fontSize=font_size,
                leading=line_spacing_to_leading(font_size, elem.get("LineSpacing", "0.2")),
            )
            txt = build_paragraph_text(elem, content_buffer)
            if txt.strip():
                flow.append(Paragraph(txt, style))
            else:
                flow.append(Spacer(1, style.leading))
            flow.append(Spacer(1, 4))
        elif elem.tag == "page-break":
            flow.append(PageBreak())

    doc.build(flow)


def main():
    if len(sys.argv) < 2:
        print("Usage: python converter.py input1.udf [input2.udf ...]")
        sys.exit(1)

    for udf_file in sys.argv[1:]:
        if not os.path.isfile(udf_file):
            print(f"Input file not found: {udf_file}")
            continue
        base, ext = os.path.splitext(udf_file)
        if ext.lower() != ".udf":
            print(f"Skipping non-UDF file: {udf_file}")
            continue

        out_pdf = base + "_light.pdf"
        try:
            udf_to_pdf_light(udf_file, out_pdf)
            print(f"PDF file created: {out_pdf}")
        except Exception as exc:
            print(f"Failed for {udf_file}: {exc}")


if __name__ == "__main__":
    main()
