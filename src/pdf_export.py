"""Экспорт КП в PDF (reportlab) с корректной кириллицей.

Шрифты: ищем TT-шрифт с кириллицей в порядке:
  1) assets/fonts/DejaVuSans (рекомендуется скачать);
  2) системные шрифты Windows (arial / segoeui / times);
  3) DejaVu из /usr/share/fonts (Linux).

Текст PDF берётся из тех же sections/структуры, что и предпросмотр (критерий A1).
"""
from __future__ import annotations

import os
import re
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config import BASE_DIR

FONT_REGULAR = "KPFont"
FONT_BOLD = "KPFont-Bold"

_fonts_registered = False


class PdfFontError(Exception):
    """Не найден шрифт, поддерживающий кириллицу."""


def _font_candidates() -> list[tuple[Path, Path | None]]:
    assets = BASE_DIR / "assets" / "fonts"
    windir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = [
        (assets / "DejaVuSans.ttf", assets / "DejaVuSans-Bold.ttf"),
        (windir / "arial.ttf", windir / "arialbd.ttf"),
        (windir / "segoeui.ttf", windir / "seguib.ttf"),
        (windir / "times.ttf", windir / "timesbd.ttf"),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
         Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
    ]
    return candidates


def register_fonts() -> None:
    """Регистрирует шрифт с кириллицей (однократно)."""
    global _fonts_registered
    if _fonts_registered:
        return
    for regular, bold in _font_candidates():
        if regular and regular.exists():
            regular = Path(regular)
            bold = Path(bold) if bold and Path(bold).exists() else None
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular)))
            if bold:
                pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold)))
                registerFontFamily(FONT_REGULAR, normal=FONT_REGULAR, bold=FONT_BOLD)
            else:
                registerFontFamily(FONT_REGULAR, normal=FONT_REGULAR, bold=FONT_REGULAR)
            _fonts_registered = True
            return
    raise PdfFontError(
        "Не найден TTF-шрифт с кириллицей. Положите DejaVuSans.ttf и "
        "DejaVuSans-Bold.ttf в assets/fonts/."
    )


def prepare_document(client, version, created_at, sections, pricing) -> dict:
    """Единый источник контента для предпросмотра и PDF (критерий A1)."""
    return {
        "client": client,
        "version": version,
        "created_at": created_at,
        "sections": list(sections),
        "pricing": list(pricing),
    }


def safe_filename(client: str, version: int) -> str:
    """Имя файла: КП_{клиент}_{YYYY-MM-DD}_v{версия}.pdf (ТЗ FR-11)."""
    from datetime import date

    safe = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", client).strip()
    safe = re.sub(r"\s+", " ", safe).strip()[:80] or "Клиент"
    return f"КП_{safe}_{date.today().isoformat()}_v{version}.pdf"


def _styles():
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "KPTitle", parent=base["Title"], fontName=FONT_BOLD, fontSize=18, leading=22
    )
    sub = ParagraphStyle(
        "KPSub", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=11,
        leading=14, textColor=colors.HexColor("#444444"),
    )
    h2 = ParagraphStyle(
        "KPH2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=13,
        leading=16, spaceBefore=10, spaceAfter=4,
    )
    body_p = ParagraphStyle(
        "KPBody", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=10.5,
        leading=15,
    )
    return title, sub, h2, body_p


def create_pdf(document: dict) -> bytes:
    """Генерирует PDF и возвращает байты. document — результат prepare_document()."""
    register_fonts()
    title_style, sub_style, h2_style, body_style = _styles()

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Коммерческое предложение",
    )
    story = [
        Paragraph("Коммерческое предложение", title_style),
        Spacer(1, 2 * mm),
        Paragraph(f"Клиент: {document['client']}", sub_style),
        Paragraph(f"Версия: v{document['version']}    Дата: {document['created_at']}", sub_style),
        Spacer(1, 2 * mm),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#999999")),
        Spacer(1, 4 * mm),
    ]

    for sec in document["sections"]:
        story.append(Paragraph(f"<b>{sec['header']}</b>", h2_style))
        for chunk in (sec.get("body") or "").split("\n"):
            chunk = chunk.strip()
            if chunk:
                story.append(Paragraph(chunk, body_style))

    if document.get("pricing"):
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("<b>Состав работ и стоимость</b>", h2_style))
        data = [["Услуга", "Стоимость"]]
        for row in document["pricing"]:
            data.append([row.get("name", ""), row.get("price_text", "")])
        table = Table(data, colWidths=[110 * mm, 60 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
                    ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)

    def _footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont(FONT_REGULAR, 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(
            18 * mm, 10 * mm,
            "Сформировано в AI-конструкторе КП • требует проверки менеджером",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()