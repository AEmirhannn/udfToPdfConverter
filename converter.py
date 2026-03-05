import os
import sys
import zipfile
import xml.etree.ElementTree as ET
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


def find_font_path(candidates):
    search_dirs = [
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
        os.path.expanduser("~/Library/Fonts"),
        "/Library/Fonts",
        "/System/Library/Fonts/Supplemental",
        "/System/Library/Fonts",
    ]

    for directory in search_dirs:
        for name in candidates:
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                return path
    return None


def configure_fonts():
    regular = find_font_path([
        "NotoSerif-Regular.ttf",
        "DejaVuSerif.ttf",
        "Times New Roman.ttf",
        "Arial Unicode.ttf",
        "Arial.ttf",
    ])
    bold = find_font_path([
        "NotoSerif-Bold.ttf",
        "DejaVuSerif-Bold.ttf",
        "Times New Roman Bold.ttf",
        "Arial Bold.ttf",
    ])
    italic = find_font_path([
        "NotoSerif-Italic.ttf",
        "DejaVuSerif-Italic.ttf",
        "Times New Roman Italic.ttf",
        "Arial Italic.ttf",
    ])
    bold_italic = find_font_path([
        "NotoSerif-BoldItalic.ttf",
        "DejaVuSerif-BoldItalic.ttf",
        "Times New Roman Bold Italic.ttf",
        "Arial Bold Italic.ttf",
    ])

    if not regular:
        raise RuntimeError("No Unicode TTF font found. Please place a TTF in this folder or /Library/Fonts")

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
