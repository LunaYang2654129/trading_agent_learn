from pathlib import Path
import re
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs" / "finrl_tensortrade_detailed_summary.md"
OUT_DIR = (
    Path.home()
    / ".codex"
    / "visualizations"
    / "2026"
    / "07"
    / "13"
    / "019f5926-8325-70d1-99a9-8a35468e3e24"
)
TARGET = OUT_DIR / (sys.argv[2] if len(sys.argv) > 2 else "finrl_tensortrade_detailed_summary.pdf")

FONT = Path("C:/Windows/Fonts/msyh.ttc")
BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")
MONO = Path("C:/Windows/Fonts/consola.ttf")

PAGE_W, PAGE_H = 2480, 3508  # A4 at 300 DPI
MARGIN_X, MARGIN_Y = 180, 170
CONTENT_W = PAGE_W - 2 * MARGIN_X

font_body = ImageFont.truetype(str(FONT), 40)
font_small = ImageFont.truetype(str(FONT), 34)
font_h1 = ImageFont.truetype(str(BOLD), 68)
font_h2 = ImageFont.truetype(str(BOLD), 52)
font_h3 = ImageFont.truetype(str(BOLD), 43)
font_code = ImageFont.truetype(str(MONO if MONO.exists() else FONT), 32)


def new_page():
    image = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    return image, ImageDraw.Draw(image), MARGIN_Y


def text_width(draw, text, font):
    if not text:
        return 0
    return draw.textlength(text, font=font)


def wrap_text(draw, text, font, max_width):
    lines = []
    current = ""
    for char in text:
        candidate = current + char
        if text_width(draw, candidate, font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines or [""]


def ensure_space(pages, draw, y, needed):
    if y + needed <= PAGE_H - MARGIN_Y:
        return pages[-1], draw, y
    page, draw, y = new_page()
    pages.append(page)
    return page, draw, y


def draw_wrapped(pages, draw, y, text, font, fill=(31, 41, 51), indent=0, gap=16, line_gap=14):
    max_width = CONTENT_W - indent
    lines = wrap_text(draw, text, font, max_width)
    line_h = font.size + line_gap
    needed = len(lines) * line_h + gap
    page, draw, y = ensure_space(pages, draw, y, needed)
    for line in lines:
        page, draw, y = ensure_space(pages, draw, y, line_h + gap)
        draw.text((MARGIN_X + indent, y), line, font=font, fill=fill)
        y += line_h
    return draw, y + gap


def normalize_markdown_line(line):
    line = line.strip()
    line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
    line = line.replace("`", "")
    line = line.replace("**", "")
    return line


def render_table(pages, draw, y, table_lines):
    rows = []
    for line in table_lines:
        if re.fullmatch(r"\s*\|?[\s:\-|]+\|?\s*", line):
            continue
        cells = [normalize_markdown_line(cell) for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    if not rows:
        return draw, y

    cols = max(len(row) for row in rows)
    col_w = CONTENT_W // cols
    row_pad = 14
    for row_index, row in enumerate(rows):
        cell_lines = []
        row_h = 0
        for col in range(cols):
            text = row[col] if col < len(row) else ""
            font = font_small if row_index else font_small
            wrapped = wrap_text(draw, text, font, col_w - 24)
            cell_lines.append(wrapped)
            row_h = max(row_h, len(wrapped) * (font.size + 8) + 2 * row_pad)

        page, draw, y = ensure_space(pages, draw, y, row_h + 6)
        x = MARGIN_X
        for wrapped in cell_lines:
            bg = (242, 244, 247) if row_index == 0 else (255, 255, 255)
            draw.rectangle((x, y, x + col_w, y + row_h), outline=(190, 190, 190), fill=bg)
            ty = y + row_pad
            for line in wrapped:
                draw.text((x + 12, ty), line, font=font_small, fill=(31, 41, 51))
                ty += font_small.size + 8
            x += col_w
        y += row_h
    return draw, y + 26


def main():
    pages = []
    page, draw, y = new_page()
    pages.append(page)

    in_code = False
    table_buffer = []

    for raw_line in SOURCE.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            in_code = not in_code
            continue

        if table_buffer and not line.strip().startswith("|"):
            draw, y = render_table(pages, draw, y, table_buffer)
            table_buffer = []

        if in_code:
            draw, y = draw_wrapped(pages, draw, y, line, font_code, fill=(54, 65, 83), gap=8)
            continue

        if not line.strip():
            y += 18
            if y > PAGE_H - MARGIN_Y:
                page, draw, y = new_page()
                pages.append(page)
            continue

        if line.strip().startswith("|"):
            table_buffer.append(line)
            continue

        clean = normalize_markdown_line(line)
        if clean.startswith("# "):
            draw, y = draw_wrapped(pages, draw, y, clean[2:], font_h1, gap=36, line_gap=20)
        elif clean.startswith("## "):
            draw, y = draw_wrapped(pages, draw, y, clean[3:], font_h2, gap=26, line_gap=18)
        elif clean.startswith("### "):
            draw, y = draw_wrapped(pages, draw, y, clean[4:], font_h3, gap=18, line_gap=14)
        elif clean.startswith("- "):
            draw, y = draw_wrapped(pages, draw, y, "• " + clean[2:], font_body, indent=28, gap=10)
        elif re.match(r"^\d+\.\s+", clean):
            draw, y = draw_wrapped(pages, draw, y, clean, font_body, indent=28, gap=10)
        else:
            draw, y = draw_wrapped(pages, draw, y, clean, font_body, gap=12)

    if table_buffer:
        draw, y = render_table(pages, draw, y, table_buffer)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages[0].save(TARGET, save_all=True, append_images=pages[1:], resolution=300)
    print(TARGET)


if __name__ == "__main__":
    main()
