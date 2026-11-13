"""Genera el PDF entregable desde documentacion/informe.md.

Uso desde la raiz del repositorio:
    $env:PYTHONPATH = 'C:\\tmp\\pasaporte_pdf_deps'
    python documentacion/generar_informe_pdf.py
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "documentacion" / "informe.md"
OUTPUT = ROOT / "output" / "pdf" / "informe_pasaporte_ba.pdf"

NAVY = HexColor("#123247")
TEAL = HexColor("#007E87")
GOLD = HexColor("#E7A923")
CREAM = HexColor("#F7F3E8")
INK = HexColor("#1F2933")
MUTED = HexColor("#5F6B73")
GRID = HexColor("#CBD5D9")
PALE_TEAL = HexColor("#E8F5F4")
PALE_GOLD = HexColor("#FFF6D9")


def registrar_fuentes() -> None:
    candidatos = [
        ("Arial", "C:/Windows/Fonts/arial.ttf"),
        ("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"),
        ("Consolas", "C:/Windows/Fonts/consola.ttf"),
    ]
    for nombre, ruta in candidatos:
        if Path(ruta).exists():
            pdfmetrics.registerFont(TTFont(nombre, ruta))


registrar_fuentes()
FONT = "Arial" if "Arial" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
BOLD = "Arial-Bold" if "Arial-Bold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
MONO = "Consolas" if "Consolas" in pdfmetrics.getRegisteredFontNames() else "Courier"


def estilos():
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName=FONT, fontSize=9.2,
            leading=13.2, textColor=INK, spaceAfter=6, alignment=TA_LEFT,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName=BOLD, fontSize=15,
            leading=18, textColor=NAVY, spaceBefore=8, spaceAfter=9,
        ),
        "h3": ParagraphStyle(
            "H3", parent=base["Heading3"], fontName=BOLD, fontSize=11.5,
            leading=14, textColor=TEAL, spaceBefore=7, spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName=FONT, fontSize=9.1,
            leading=12.8, leftIndent=13, firstLineIndent=-7, textColor=INK, spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "Code", parent=base["Code"], fontName=MONO, fontSize=7.5,
            leading=10, leftIndent=7, rightIndent=7, textColor=NAVY,
            backColor=HexColor("#EEF2F3"), borderPadding=7, spaceBefore=3, spaceAfter=8,
        ),
        "table": ParagraphStyle(
            "Table", parent=base["BodyText"], fontName=FONT, fontSize=7.1,
            leading=9.3, textColor=INK,
        ),
        "table_head": ParagraphStyle(
            "TableHead", parent=base["BodyText"], fontName=BOLD, fontSize=7.2,
            leading=9.5, textColor=colors.white,
        ),
        "caption": ParagraphStyle(
            "Caption", parent=base["BodyText"], fontName=FONT, fontSize=7.5,
            leading=10, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8,
        ),
    }


S = estilos()


def inline(texto: str) -> str:
    texto = html.escape(texto.strip(), quote=False)
    texto = re.sub(r"&lt;(https?://[^&]+?)&gt;", r'<link href="\1" color="#007E87">\1</link>', texto)
    texto = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="#007E87">\1</link>', texto)
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"`([^`]+)`", rf'<font name="{MONO}" color="#006B73">\1</font>', texto)
    texto = re.sub(r"\*(.+?)\*", r"<i>\1</i>", texto)
    return texto


class DerResumen(Flowable):
    """DER legible dividido en catálogo y actividad para evitar cruces."""

    def __init__(self, ancho: float):
        super().__init__()
        self.width = ancho
        self.height = 330

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFont(BOLD, 10)
        c.setFillColor(NAVY)
        c.drawString(0, 315, "DER — catálogo normalizado")

        def caja(x, y, w, titulo, campos, color=PALE_TEAL):
            h = 52
            c.setFillColor(color)
            c.setStrokeColor(TEAL)
            c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
            c.setFillColor(NAVY)
            c.setFont(BOLD, 7.5)
            c.drawString(x + 6, y + h - 12, titulo)
            c.setFillColor(INK)
            c.setFont(FONT, 5.8)
            for n, campo in enumerate(campos[:4]):
                c.drawString(x + 6, y + h - 23 - n * 8, campo)
            return (x, y, w, h)

        def unir(a, b, izq, der):
            ax, ay, aw, ah = a
            bx, by, bw, bh = b
            x1, y1 = ax + aw, ay + ah / 2
            x2, y2 = bx, by + bh / 2
            c.setStrokeColor(MUTED)
            c.setLineWidth(0.8)
            c.line(x1, y1, x2, y2)
            c.setFillColor(MUTED)
            c.setFont(BOLD, 5.8)
            c.drawString(x1 + 2, y1 + 3, izq)
            c.drawRightString(x2 - 2, y2 + 3, der)

        gap = 12
        w = (self.width - gap * 4) / 5
        y = 245
        comuna = caja(0, y, w, "COMUNA", ["PK id_comuna"])
        barrio = caja(w + gap, y, w, "BARRIO", ["PK id_barrio", "FK id_comuna"])
        lugar = caja((w + gap) * 2, y, w, "LUGAR", ["PK id_lugar", "FK barrio?", "FK categoría", "FK fuente?"])
        categoria = caja((w + gap) * 3, y, w, "CATEGORÍA", ["PK id_categoria", "FK id_tipo"])
        tipo = caja((w + gap) * 4, y, w, "TIPO_LUGAR", ["PK id_tipo"])
        unir(comuna, barrio, "1", "N")
        unir(barrio, lugar, "0..1", "N")
        unir(lugar, categoria, "N", "1")
        unir(categoria, tipo, "N", "1")
        fuente = caja(205, 178, 105, "FUENTE", ["PK id_fuente", "url / fecha"], PALE_GOLD)
        c.setStrokeColor(MUTED)
        c.line(257, 230, 257, 245)
        c.setFont(BOLD, 5.8)
        c.setFillColor(MUTED)
        c.drawString(261, 233, "0..1 : N")

        c.setFont(BOLD, 10)
        c.setFillColor(NAVY)
        c.drawString(0, 153, "DER — actividad, seguridad y moderación")
        user = caja(0, 83, 100, "USUARIO", ["PK id_usuario", "UK nombre / email", "rol"])
        checkin = caja(138, 83, 100, "CHECKIN", ["PK id_checkin", "FK usuario", "FK lugar"])
        favorito = caja(276, 83, 100, "FAVORITO", ["PK/FK usuario", "PK/FK lugar"])
        sesion = caja(414, 83, 100, "SESIÓN", ["PK id_sesion", "FK usuario", "UK token_hash"])
        sugerencia = caja(138, 12, 132, "SUGERENCIA_LUGAR", ["PK id_sugerencia", "FK autor / revisor?", "FK lugar_creado? UK"], PALE_GOLD)
        lugar_ref = caja(324, 12, 100, "LUGAR", ["entidad catálogo"], PALE_GOLD)
        unir(user, checkin, "1", "N")
        unir(checkin, favorito, "N", "N")
        unir(favorito, sesion, "N", "N")
        c.setStrokeColor(MUTED)
        c.line(50, 83, 160, 64)
        c.line(270, 38, 324, 38)
        c.line(374, 64, 374, 83)
        c.setFont(BOLD, 5.8)
        c.setFillColor(MUTED)
        c.drawString(52, 68, "autor 1 : N")
        c.drawString(277, 42, "0..1 : 0..1")
        c.drawString(378, 69, "LUGAR 1 : N")
        c.setFont(FONT, 6)
        c.drawString(0, 2, "CHECKIN y FAVORITO resuelven las relaciones N:M entre USUARIO y LUGAR.")
        c.restoreState()


class Benchmark(Flowable):
    def __init__(self, ancho: float):
        super().__init__()
        self.width = ancho
        self.height = 155
        self.filas = [
            ("Historial", 3.6, 8.3),
            ("Actividad/lugar", 3.8, 8.3),
            ("Ranking activo", 24.0, 14.0),
            ("Pasaporte activo", 172.2, 27.1),
        ]

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(NAVY)
        c.setFont(BOLD, 9)
        c.drawString(0, 142, "Mediana con 1.000.001 check-ins (ms; menor es mejor)")
        x0, y0 = 115, 20
        maximo = 180
        escala = (self.width - x0 - 25) / maximo
        for i, (nombre, mysql, hbase) in enumerate(self.filas):
            y = 112 - i * 27
            c.setFillColor(INK)
            c.setFont(FONT, 7)
            c.drawRightString(x0 - 7, y + 3, nombre)
            c.setFillColor(TEAL)
            c.rect(x0, y + 7, mysql * escala, 7, fill=1, stroke=0)
            c.setFillColor(GOLD)
            c.rect(x0, y - 2, hbase * escala, 7, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont(FONT, 5.8)
            c.drawString(x0 + mysql * escala + 3, y + 7, f"{mysql:.1f}")
            c.drawString(x0 + hbase * escala + 3, y - 2, f"{hbase:.1f}")
        c.setFillColor(TEAL)
        c.rect(x0, 2, 10, 6, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(FONT, 6.5)
        c.drawString(x0 + 14, 2, "MySQL")
        c.setFillColor(GOLD)
        c.rect(x0 + 65, 2, 10, 6, fill=1, stroke=0)
        c.setFillColor(INK)
        c.drawString(x0 + 79, 2, "HBase")
        c.restoreState()


def tabla_markdown(lineas: list[str], ancho: float) -> Table:
    filas = []
    for idx, linea in enumerate(lineas):
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        estilo = S["table_head"] if idx == 0 else S["table"]
        filas.append([Paragraph(inline(c), estilo) for c in celdas])
    columnas = len(filas[0])
    if columnas == 2:
        widths = [ancho * 0.28, ancho * 0.72]
    elif columnas == 3:
        widths = [ancho * 0.27, ancho * 0.37, ancho * 0.36]
    elif columnas == 4:
        widths = [ancho * 0.24, ancho * 0.28, ancho * 0.24, ancho * 0.24]
    elif columnas == 6:
        widths = [ancho * 0.13, ancho * 0.15, ancho * 0.08, ancho * 0.32, ancho * 0.18, ancho * 0.14]
    else:
        widths = [ancho / columnas] * columnas
    tabla = Table(filas, colWidths=widths, repeatRows=1, hAlign="LEFT")
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#F6F8F8")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def portada(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 92 * mm, w, 92 * mm, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.circle(w - 34 * mm, h - 37 * mm, 23 * mm, fill=1, stroke=0)
    canvas.setFillColor(GOLD)
    canvas.circle(w - 22 * mm, h - 55 * mm, 10 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont(BOLD, 30)
    canvas.drawString(24 * mm, h - 43 * mm, "Pasaporte BA")
    canvas.setFont(FONT, 13)
    canvas.drawString(24 * mm, h - 55 * mm, "Arquitectura y modelado de datos")
    canvas.setFont(BOLD, 10)
    canvas.drawString(24 * mm, h - 72 * mm, "TP Integrador — Bases de Datos")
    canvas.setFillColor(INK)
    canvas.setFont(BOLD, 13)
    canvas.drawString(24 * mm, h - 120 * mm, "Informe técnico final")
    canvas.setFont(FONT, 10)
    canvas.drawString(24 * mm, h - 134 * mm, "Tecnicatura en Programación Informática — UNSAM")
    canvas.drawString(24 * mm, h - 142 * mm, "Docentes: Gabriel Flores y Rodrigo Casco")
    canvas.drawString(24 * mm, h - 150 * mm, "Integrantes: completar con los cinco nombres")
    canvas.drawString(24 * mm, h - 158 * mm, "Noviembre de 2026")
    etiquetas = [("MYSQL 8.4", TEAL), ("HBASE 2.1", GOLD), ("FASTAPI", NAVY), ("EXPO 58", TEAL)]
    x = 24 * mm
    for texto, color in etiquetas:
        canvas.setFillColor(color)
        canvas.roundRect(x, h - 188 * mm, 34 * mm, 10 * mm, 4 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont(BOLD, 7.5)
        canvas.drawCentredString(x + 17 * mm, h - 184.5 * mm, texto)
        x += 39 * mm
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7.5)
    canvas.drawString(24 * mm, 20 * mm, "github.com/camitermine/Pasaporte-BA")
    canvas.restoreState()


def pagina(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(GRID)
    canvas.line(doc.leftMargin, h - 16 * mm, w - doc.rightMargin, h - 16 * mm)
    canvas.setFont(FONT, 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, h - 12 * mm, "PASAPORTE BA — INFORME DEL TP INTEGRADOR")
    canvas.drawRightString(w - doc.rightMargin, 11 * mm, f"Página {doc.page}")
    canvas.restoreState()


def construir_historia(texto: str, ancho: float):
    lineas = texto.splitlines()
    historia = []
    i = 0
    parrafo: list[str] = []
    en_codigo = False
    codigo: list[str] = []

    def volcar_parrafo():
        nonlocal parrafo
        if parrafo:
            historia.append(Paragraph(inline(" ".join(x.strip() for x in parrafo)), S["body"]))
            parrafo = []

    while i < len(lineas):
        linea = lineas[i]
        if i == 0 and linea.startswith("# "):
            i += 1
            while i < len(lineas) and not lineas[i].startswith("## "):
                i += 1
            historia.append(PageBreak())
            continue
        if linea.startswith("```"):
            volcar_parrafo()
            if en_codigo:
                historia.append(Preformatted("\n".join(codigo), S["code"]))
                codigo = []
                en_codigo = False
            else:
                en_codigo = True
            i += 1
            continue
        if en_codigo:
            codigo.append(linea)
            i += 1
            continue
        if linea.startswith("## "):
            volcar_parrafo()
            titulo = linea[3:].strip()
            historia.append(CondPageBreak(38 * mm))
            historia.append(Paragraph(inline(titulo), S["h2"]))
            if titulo.startswith("5."):
                historia.extend([DerResumen(ancho), Paragraph("Figura 1. DER resumido. El detalle de atributos y cardinalidades se conserva en <font name=\"Consolas\">documentacion/DER.md</font>.", S["caption"])])
            if titulo.startswith("14."):
                historia.extend([Benchmark(ancho), Paragraph("Figura 2. El costo fijo de HBase penaliza lecturas pequeñas; sus agregados resultan ventajosos al crecer el volumen.", S["caption"])])
            i += 1
            continue
        if linea.startswith("### "):
            volcar_parrafo()
            historia.append(Paragraph(inline(linea[4:]), S["h3"]))
            i += 1
            continue
        if linea.startswith("|") and i + 1 < len(lineas) and re.match(r"^\|[\s:|-]+\|$", lineas[i + 1]):
            volcar_parrafo()
            tabla = [linea]
            i += 2
            while i < len(lineas) and lineas[i].startswith("|"):
                tabla.append(lineas[i])
                i += 1
            historia.extend([tabla_markdown(tabla, ancho), Spacer(1, 7)])
            continue
        m = re.match(r"^[-*] (.+)$", linea)
        if m:
            volcar_parrafo()
            historia.append(Paragraph("• " + inline(m.group(1)), S["bullet"]))
            i += 1
            continue
        m = re.match(r"^(\d+)\. (.+)$", linea)
        if m:
            volcar_parrafo()
            historia.append(Paragraph(f"{m.group(1)}. " + inline(m.group(2)), S["bullet"]))
            i += 1
            continue
        if not linea.strip():
            volcar_parrafo()
            i += 1
            continue
        if linea.strip() == "---":
            volcar_parrafo()
            i += 1
            continue
        parrafo.append(linea)
        i += 1
    volcar_parrafo()
    return historia


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    texto = SOURCE.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=19 * mm, rightMargin=19 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm,
        title="Pasaporte BA — Informe del TP Integrador",
        author="Equipo Pasaporte BA",
        subject="Modelado relacional MySQL y NoSQL HBase",
    )
    historia = construir_historia(texto, A4[0] - doc.leftMargin - doc.rightMargin)
    doc.build(historia, onFirstPage=portada, onLaterPages=pagina)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
