"""Builds Team PARAKRAM's 6-slide SIH 2026 idea deck for SIH26253 (JalSatya) on the official SIH template.

    python build_deck.py      ->  PARAKRAM_SIH26253_JalSatya.pptx
    soffice --headless --convert-to pdf PARAKRAM_SIH26253_JalSatya.pptx

The template's SIH artwork, logos, bottom bar, slide numbers, section titles and idea-detail pointers are kept.
Only the content inside each slide is replaced. Every simulated number comes from ../sim/results.json or from the
demo's village twin, and is labelled simulated on the slide.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageFont
from pptx import Presentation
from pptx.chart.data import XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

HERE = Path(__file__).resolve().parent
TEMPLATE = Path("/mnt/user-data/uploads/SIH_2026/SIH26264_SAMANVAY/docs/deck/template/PARAKRAM_template.pptx")
OUT = HERE / "PARAKRAM_SIH26253_JalSatya.pptx"
IMG = HERE / "img"
RES = json.loads((HERE.parent / "sim" / "results.json").read_text())
TEAM_ID = "151508"
LINKS = {"demo": "codedbysuryansh.github.io/PARAKRAM-SIH26253", "code": "github.com/codedbysuryansh/PARAKRAM-SIH26253",
         "video": "youtu.be/rtyKnEUzjjI"}
URLS = {"demo": "https://codedbysuryansh.github.io/PARAKRAM-SIH26253/",
        "code": "https://github.com/codedbysuryansh/PARAKRAM-SIH26253", "video": "https://youtu.be/rtyKnEUzjjI"}


def bump(sz):
    """Final pass: no running text below 12 pt on a projected slide."""
    return sz if sz >= 13 else min(13.0, sz + 1.5)
# village twin numbers read from the running demo (scratchpad twinnums.py): 120 taps, max water age 24 h
_tw = RES["twin"]   # sim/jalsatya_sim.py village_twin(), run on the demo's own 120-tap village (sim/village.json)
TWIN = dict(habit=_tw["habit_dose"], before=_tw["habit_safe"], tail_before=_tw["habit_tail"], rec=_tw["recommended_dose"],
            after=_tw["twin_safe"], tail_after=_tw["twin_tail"], n=_tw["taps"], tests=_tw["tests_used"])
TAGLINE = "No strip, no record. No guesswork at the tap."

C = dict(ink="13315C", navy="0E1330", body="1A2233", muted="4A5568", line="D5DEE8", soft="E9F0F8", tap="2F7FC1",
         tap_l="E3EEF8", safe="1F8A5B", safe_l="E2F3EA", low="C8412D", low_l="FBE9E5", high="C27C0E", white="FFFFFF",
         grey="8A94A3")
F, FC = "Barlow", "Barlow Condensed"
FONTS = {(F, False): "/root/.fonts/Barlow-Regular.ttf", (F, True): "/root/.fonts/Barlow-Bold.ttf",
         (FC, False): "/root/.fonts/BarlowCondensed-Medium.ttf", (FC, True): "/root/.fonts/BarlowCondensed-Bold.ttf"}
_font_cache: dict = {}
WARN: list[str] = []


def I(x):
    return int(round(x * 914400))


def rgb(h):
    return RGBColor.from_string(h)


# ----------------------------------------------------------------------------------------------- text fitting check
def _f(name, bold):
    key = (name, bool(bold))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FONTS.get(key, FONTS[(F, bool(bold))]), 200)
    return _font_cache[key]


def lines_needed(runs, width_in, size, font, bold):
    """Greedy word wrap of a paragraph made of runs, using real font metrics (inches)."""
    words = []
    for text, o in runs:
        fnt = _f(o.get("font", font), o.get("bold", bold))
        sz = bump(o.get("size", size))
        for w in text.split(" "):
            words.append((w, fnt, sz))
    n, cur = 1, 0.0
    for w, fnt, sz in words:
        wlen = fnt.getlength(w) * sz / 200 / 72
        space = fnt.getlength(" ") * sz / 200 / 72
        add = wlen if cur == 0 else wlen + space
        if cur > 0 and cur + add > width_in:
            n += 1
            cur = wlen
        else:
            cur += add
    return n


def check_fit(label, paras, w, h, size, font, bold, lnspc, after):
    if w <= 0 or h <= 0:
        return
    total = 0.0
    for para in paras:
        runs = [para] if isinstance(para, (str, tuple)) else para
        runs = [(r, {}) if isinstance(r, str) else r for r in runs]
        sz = max(bump(o.get("size", size)) for _, o in runs)
        n = lines_needed(runs, w, size, font, bold)
        total += n * sz * 1.2 * (lnspc or 1.0) / 72 + after / 72
    total -= after / 72
    if total > h + 0.03:
        WARN.append(f"{label}: needs {total:.2f} in, box {h:.2f} in :: {str(paras)[:70]}")


# ----------------------------------------------------------------------------------------------- shape helpers
def flat(shp):
    """Drop the theme style reference so no renderer adds its default drop shadow."""
    st = shp._element.find(qn("p:style"))
    if st is not None:
        shp._element.remove(st)


def box(s, x, y, w, h, fill="FFFFFF", line=C["line"], radius=6000, lw=9525, shape=None):
    shp = s.shapes.add_shape(shape or MSO_SHAPE.ROUNDED_RECTANGLE, I(x), I(y), I(w), I(h))
    if shape is None:
        shp.adjustments[0] = radius / 100000
    if fill:
        shp.fill.solid(); shp.fill.fore_color.rgb = rgb(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = rgb(line); shp.line.width = Emu(lw)
    else:
        shp.line.fill.background()
    sp = shp._element.spPr
    if sp.find(qn("a:effectLst")) is None:
        sp.append(sp.makeelement(qn("a:effectLst"), {}))
    flat(shp)
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return shp


def tb(s, x, y, w, h, paras, size=13, font=F, color=C["body"], bold=False, align="l", anchor="t", lnspc=None,
       after=0, shape=None, label="text"):
    if shape is None:
        check_fit(label, paras, w, h, size, font, bold, lnspc, after)
    t = shape if shape is not None else s.shapes.add_textbox(I(x), I(y), I(w), I(h))
    tf = t.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    bp = tf._txBody.find(qn("a:bodyPr"))
    for ch in list(bp):
        bp.remove(ch)
    bp.append(bp.makeelement(qn("a:noAutofit"), {}))
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        p.space_after = Pt(after)
        if lnspc:
            p.line_spacing = lnspc
        runs = [para] if isinstance(para, (str, tuple)) else para
        for r in runs:
            text, o = (r, {}) if isinstance(r, str) else r
            run = p.add_run(); run.text = text
            f = run.font
            f.name = o.get("font", font); f.size = Pt(bump(o.get("size", size))); f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False); f.color.rgb = rgb(o.get("color", color))
            if o.get("link"):
                run.hyperlink.address = o["link"]
                f.color.rgb = rgb(o.get("color", color))      # keep our colour, not the theme's link colour
    return t


def pointer(s, x, y, w, text, color=None, size=11.5):
    """The template's idea-detail pointers, text kept exactly as in the official SIH template."""
    return tb(s, x, y, w, 0.26, [text], size=size, bold=True, color=color or C["ink"], label="pointer")


def picture(s, path, x, y, w=None, h=None, border=True):
    img = Image.open(path); iw, ih = img.size
    if w and not h:
        h = w * ih / iw
    elif h and not w:
        w = h * iw / ih
    pic = s.shapes.add_picture(str(path), I(x), I(y), I(w), I(h))
    if border:
        pic.line.color.rgb = rgb(C["line"]); pic.line.width = Emu(9525)
    return pic, w, h


def arrow(s, x1, y1, x2, y2, color=C["grey"], width=1.5):
    ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, I(x1), I(y1), I(x2), I(y2))
    flat(ln)
    ln.line.color.rgb = rgb(color); ln.line.width = Pt(width)
    lnel = ln.line._get_or_add_ln()
    lnel.append(lnel.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return ln


def clear_content(s):
    for shp in list(s.shapes):
        keep = (shp.is_placeholder or (shp.shape_type == 1 and shp.top >= 6300000)
                or (shp.shape_type == 1 and shp.top < 400000 and shp.left < 400000)
                or (shp.shape_type == 13 and (shp.left > 9000000 or (shp.left < 700000 and shp.top < 700000))))
        if not keep:
            el = shp._element
            for blip in el.iter(qn("a:blip")):
                rid = blip.get(qn("r:embed"))
                if rid:
                    try:
                        s.part.drop_rel(rid)
                    except Exception:
                        pass
            for ch in el.iter(qn("c:chart")):
                rid = ch.get(qn("r:id"))
                if rid:
                    try:
                        s.part.drop_rel(rid)
                    except Exception:
                        pass
            el.getparent().remove(el)


def set_title(s, text):
    for shp in s.placeholders:
        if "TITLE" in str(shp.placeholder_format.type):
            runs = shp.text_frame.paragraphs[0].runs
            runs[0].text = text
            for r in runs[1:]:
                r.text = ""
            return


def subtitle(s, text):
    tb(s, 2.6, 0.86, 8.1, 0.34, [text], size=16, font=FC, bold=True, color=C["muted"], align="c", label="subtitle")


def number_block(s, x, y, w, h, big, small, color=None, big_size=28, fill="FFFFFF", line=C["line"], unit=None):
    box(s, x, y, w, h, fill=fill, line=line)
    runs = [(big, {})] + ([(" " + unit, {"size": big_size * 0.5, "color": C["muted"]})] if unit else [])
    tb(s, x + 0.15, y + 0.07, w - 0.28, 0.5, [runs], size=big_size, font=FC, bold=True, color=color or C["ink"],
       label="big")
    tb(s, x + 0.15, y + 0.55, w - 0.26, h - 0.6, [small], size=10.5, color=C["body"], lnspc=0.95, label="small")


def bullets(items, color=C["tap"]):
    return [[("•  ", {"color": color, "bold": True}), (t, {})] for t in items]


def chart_style(ch, legend=True):
    ch.font.name = F
    ch.font.size = Pt(10.5)
    if legend:
        ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(10.5); ch.legend.font.name = F
    else:
        ch.has_legend = False


def axis_style(ax, title, grid=False, minimum=None, maximum=None, major=None, fmt=None):
    ax.tick_labels.font.size = Pt(10); ax.tick_labels.font.name = F
    ax.tick_labels.font.color.rgb = rgb(C["muted"])
    if fmt:
        ax.tick_labels.number_format = fmt; ax.tick_labels.number_format_is_linked = False
    ax.has_major_gridlines = grid
    if grid:
        ax.major_gridlines.format.line.color.rgb = rgb("E3E9F0")
    ax.format.line.color.rgb = rgb("C3CDD8")
    if minimum is not None:
        ax.minimum_scale = minimum
    if maximum is not None:
        ax.maximum_scale = maximum
    if major is not None:
        ax.major_unit = major
    ax.has_title = True
    ax.axis_title.text_frame.text = title
    r = ax.axis_title.text_frame.paragraphs[0].runs[0]
    r.font.size = Pt(10); r.font.name = F; r.font.bold = False; r.font.color.rgb = rgb(C["muted"])


# ----------------------------------------------------------------------------------------------- slide 1
def slide1(s):
    for shp in s.shapes:
        if shp.name == "TextBox 9":
            vals = ["SIH26253",
                    "Development of Strip-Based Water Quality Test Kits for Assessment of Free Residual Chlorine "
                    "(FRC) with Sensitivity up to 0.1 ppm for Field-Level Applications",
                    "Clean & Green Technology", "Hardware", TEAM_ID, "PARAKRAM"]
            for para, v in zip(shp.text_frame.paragraphs, vals):
                para.runs[1].text = v
                for r in para.runs[2:]:
                    r.text = ""
        elif shp.name == "TextBox 39":
            ps = shp.text_frame.paragraphs
            r0 = ps[0].runs[0]
            r0.text = "JalSatya "
            for r in ps[0].runs[1:]:
                r.text = ""
            # Devanagari name in its own run so it falls back to a Devanagari font cleanly
            r1 = ps[0].add_run(); r1.text = "(जलसत्य)"
            r1.font.bold = True; r1.font.color.rgb = rgb(C["navy"])
            r1.font.name = "Noto Sans Devanagari"
            rpr = r1._r.get_or_add_rPr()
            for tag in ("a:ea", "a:cs"):
                rpr.append(rpr.makeelement(qn(tag), {"typeface": "Noto Sans Devanagari"}))
            ps[1].runs[0].text = "A chlorine test with proof built in"
            for r in ps[1].runs[1:]:
                r.text = ""
            for p in ps:
                for r in p.runs:
                    r.font.size = Pt(28)
            r1.font.size = Pt(24)
        elif shp.name == "TextBox 40":
            shp.text_frame.paragraphs[0].runs[0].text = TAGLINE
            for r in shp.text_frame.paragraphs[0].runs[1:]:
                r.text = ""


# ----------------------------------------------------------------------------------------------- slide 2
def slide2(s):
    clear_content(s)
    set_title(s, "EVERY TEST LEAVES PROOF")
    subtitle(s, "A dye-free strip designed to read free chlorine to 0.1 ppm, with proof of every test")
    pointer(s, 0.45, 1.24, 7.2, "Proposed Solution (Describe your Idea/Solution/Prototype)")

    # the problem, in the ministry's and the auditor's own words
    box(s, 0.45, 1.56, 7.25, 0.94, fill=C["low_l"], line=None)
    tb(s, 0.65, 1.64, 6.9, 0.8, [
        [("JJM's 2021 framework [1]: ", {"bold": True, "color": C["low"]}),
         ("“the availability and usage of these kits is unknown.”", {})],
        [("CAG audit, 2026 [2]: ", {"bold": True, "color": C["low"]}),
         ("more tests shown than samples received in four Thane villages.", {})],
        [("With JalSatya, no strip means no record, and every record carries its proof.",
          {"bold": True, "color": C["ink"]})],
    ], size=12.5, lnspc=1.0, after=2, label="hook")

    blocks = [
        ("Detailed explanation of the proposed solution",
         ["Dry printed-carbon strip with a buffer pad. No colour dye.",
          "A pocket reader turns its current into mg/L, about 10 s from dip to result.",
          "Each result is signed with strip serial, GPS and time, ready for WQMIS."]),
        ("How it addresses the problem",
         ["Nothing to judge by eye [5]: one button, Hindi voice, works offline.",
          "One serial per strip, so tests reported can never exceed strips issued."]),
        ("Innovation and uniqueness of the solution",
         ["Proof-of-Test: a serialised, signed strip. No real electrode curve, no record.",
          "A village twin turns verified readings into the right dose, and flags readings that do not fit the tap."]),
    ]
    size, lh = 13, 13 * 1.2 / 72
    heights = []
    for head, items in blocks:
        n = sum(lines_needed([("•  " + t, {})], 6.85, size, F, False) for t in items)
        heights.append(0.42 + n * lh + 0.045 * (len(items) - 1) + 0.16)
    top, bottom = 2.62, 6.85
    gap = (bottom - top - sum(heights)) / (len(blocks) - 1)
    pad = 0.0
    if gap > 0.24:                                   # spend extra room inside the cards, not between them
        pad = (gap - 0.24) * (len(blocks) - 1) / len(blocks)
        gap = 0.24
    if gap < 0.1:
        WARN.append(f"slide2 left column is tight: gap {gap:.2f}")
    y = top
    for (head, items), bh in zip(blocks, heights):
        bh += pad
        box(s, 0.45, y, 7.25, bh)
        pointer(s, 0.63, y + 0.12 + pad / 2, 6.9, head, color=C["tap"])
        tb(s, 0.63, y + 0.44 + pad / 2, 6.95, bh - 0.5 - pad / 2, bullets(items), size=size, lnspc=1.0, after=3.2,
           label="block")
        y += bh + gap

    # the product, and what it refuses
    box(s, 7.95, 1.56, 4.93, 5.29, fill=C["soft"], line=None)
    _, pw, _ = picture(s, IMG / "phone_result.png", 8.1, 1.7, h=5.0, border=False)
    x2 = 8.1 + pw + 0.12
    w2 = 12.88 - 0.12 - x2
    tb(s, x2, 1.78, w2, 0.46, ["Tried in our demo, and refused"], size=12.5, bold=True, color=C["ink"], lnspc=0.95,
       label="tries head")
    tries = [("Typed number", "no electrode signal"), ("Same strip twice", "serial already spent"),
             ("Copied curve", "fingerprint seen before"), ("Invented curve", "unsigned, wrong physics")]
    yy = 2.32
    for head, why in tries:
        box(s, x2, yy, w2, 0.78, fill=C["white"], line=C["line"])
        tb(s, x2 + 0.12, yy + 0.08, w2 - 0.2, 0.28, [head], size=12, bold=True, color=C["body"], label="try")
        tb(s, x2 + 0.12, yy + 0.37, w2 - 0.2, 0.38, [[("Refused: ", {"bold": True, "color": C["low"]}), (why, {})]],
           size=10.5, lnspc=0.95, label="try why")
        yy += 0.87
    tb(s, x2, yy + 0.04, w2, 1.0, ["Simulated: all 2,000 fakes across the 5 attacks we modelled were refused; "
                                   "99.3% of real tests were accepted."],
       size=10.5, color=C["muted"], lnspc=0.98, label="tries foot")


# ----------------------------------------------------------------------------------------------- slide 3
def slide3(s):
    clear_content(s)
    set_title(s, "TECHNICAL APPROACH")
    subtitle(s, "Measured by electrochemistry, not by eye, and signed before it leaves the reader")
    pointer(s, 0.45, 1.24, 9, "Technologies to be used (e.g. programming languages, frameworks, hardware)")
    chips = ["Screen-printed carbon electrode strip", "Dried buffer pad, pH 5.5", "Potentiostat front end",
             "ESP32 reader, C firmware", "BLE and USB-C", "Android app in Kotlin, offline first",
             "Ed25519 signed records", "WQMIS sync", "Python physics model", "Web dashboard, ECharts"]
    x, y = 0.45, 1.56
    fnt = _f(F, True)
    for t in chips:
        w = fnt.getlength(t) * bump(11) / 200 / 72 + 0.3
        if x + w > 12.88:
            x, y = 0.45, y + 0.41
        b = box(s, x, y, w, 0.32, fill=C["white"], line=C["line"], radius=50000)
        tb(s, 0, 0, 0, 0, [t], size=11, bold=True, color=C["ink"], align="c", anchor="m", shape=b)
        x += w + 0.09

    pointer(s, 0.45, 2.45, 9, "Methodology and process for implementation (Flow Charts/Images/ working prototype)")
    steps = [("Scan", "Strip serial and expiry checked, assigned tap shown"),
             ("Dip and read", "3 s dip, then a 5 s current reading"),
             ("Verify", "One-time strip, reader signature, curve shape"),
             ("Sync", "Signed record to WQMIS, queued when offline"),
             ("Advise", "Twin updates the dose and the next taps to test")]
    x = 0.45
    hf = _f(F, True)
    for i, (h, t) in enumerate(steps, 1):
        o = box(s, x, 2.8, 0.32, 0.32, fill=C["ink"], line=None, shape=MSO_SHAPE.OVAL)
        tb(s, 0, 0, 0, 0, [str(i)], size=12, font=FC, bold=True, color=C["white"], align="c", anchor="m", shape=o)
        tb(s, x + 0.42, 2.78, 1.95, 0.3, [h], size=13.5, bold=True, color=C["ink"], label="step head")
        tb(s, x + 0.42, 3.08, 1.95, 0.62, [t], size=11, color=C["muted"], lnspc=0.95, label="step text")
        if i < len(steps):
            hw = hf.getlength(h) * 13.5 / 200 / 72
            arrow(s, x + 0.42 + hw + 0.12, 2.96, x + 2.4, 2.96)
        x += 2.5

    # A: the hardware, as a design drawing
    box(s, 0.45, 3.86, 3.4, 2.99)
    tb(s, 0.62, 3.94, 3.1, 0.3, ["Strip and reader (design)"], size=12.5, bold=True, color=C["ink"], label="hw title")
    hw = Image.open(IMG / "hardware.png"); hw_w = 2.5 * hw.size[0] / hw.size[1]
    picture(s, IMG / "hardware.png", 0.45 + (3.4 - hw_w) / 2, 4.27, h=2.5, border=False)

    # B: native chart of the strip current for three samples, from the prototype's physics model
    box(s, 3.98, 3.86, 3.5, 2.99)
    tb(s, 4.14, 3.94, 3.2, 0.3, ["Prototype strip current (simulated)"], size=12.5, bold=True, color=C["ink"],
       label="chart title")
    t_s = RES["t_s"]
    cd = XyChartData()
    for key, name in (("1.2", "1.20 mg/L"), ("0.32", "0.32 mg/L"), ("0.0", "No chlorine")):
        ser = cd.add_series(name)
        for t, v in zip(t_s, RES["sample_traces"][key]):
            if t >= 0.3:
                ser.add_data_point(t, v)
    gf = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS, I(4.02), I(4.2), I(3.42), I(2.6), cd)
    ch = gf.chart
    chart_style(ch)
    ch.legend.font.size = Pt(9.5)
    for ser, col, wd in zip(ch.series, (C["ink"], C["tap"], C["grey"]), (2.5, 2.5, 1.75)):
        ser.format.line.color.rgb = rgb(col); ser.format.line.width = Pt(wd); ser.smooth = False
    axis_style(ch.value_axis, "Current (nA)", grid=True, minimum=0, maximum=1000, major=250, fmt="0")
    axis_style(ch.category_axis, "Seconds after dipping", minimum=0, maximum=5, major=1, fmt="0")

    # C: why the number and the record can be trusted
    box(s, 7.61, 3.86, 5.27, 2.99, fill=C["soft"], line=None)
    tb(s, 7.78, 3.96, 2.45, 0.3, ["Why the reading is true"], size=13, bold=True, color=C["ink"], label="c1 head")
    tb(s, 7.78, 4.3, 2.45, 2.5, [
        [("Current falls as Cottrell's law says", {"color": C["muted"], "size": 10.5})],
        [("i = nFAC √(D / πt)", {"font": FC, "size": 18, "bold": True, "color": C["ink"]})],
        [("About 43 nA for every 0.1 mg/L at 1 s on a 3 mm electrode.", {})],
        [("Share of chlorine the electrode sees, as HOCl", {"color": C["muted"], "size": 10.5})],
        [("f = 1 / (1 + 10^(pH − 7.54))", {"font": FC, "size": 14, "bold": True, "color": C["ink"]})],
        [("99% at the pad's pH 5.5, for water from pH 6 to 9.", {})],
    ], size=11, lnspc=0.98, after=3, label="c1 body")
    tb(s, 10.42, 3.96, 2.36, 0.3, ["Why the record is real"], size=13, bold=True, color=C["ink"], label="c2 head")
    locks = [("One strip, one test", "the serial is spent on first use"),
             ("Signed at the source", "the reader signs the raw curve, place and time"),
             ("Physics check", "a real curve falls as 1/√t; every fake shape we modelled failed")]
    yy = 4.32
    for h, t in locks:
        tb(s, 10.42, yy, 2.36, 0.8, [[(h, {"bold": True, "color": C["safe"]})], t], size=11, lnspc=0.97,
           label="lock")
        yy += 0.82


# ----------------------------------------------------------------------------------------------- slide 4
def slide4(s):
    clear_content(s)
    set_title(s, "FEASIBILITY AND VIABILITY")
    subtitle(s, "Method, maths and software are built. The working strip comes to the finale.")
    cal = RES["calibration"]
    pointer(s, 0.45, 1.24, 7.2, "Analysis of the feasibility of the idea")
    nums = [(f"{cal['lod_mgL']:.3f}", "mg/L", "detection limit, under 0.1 ppm"),
            (f"{cal['within_01'] * 100:.0f}%", None, "of readings within ±0.1 mg/L"),
            ("10 s", None, "from dip to a signed result"),
            ("100%", None, "of 2,000 simulated fakes refused")]
    x = 0.45
    for big, unit, small in nums:
        number_block(s, x, 1.56, 1.73, 1.1, big, small, big_size=27, unit=unit)
        x += 1.84
    tb(s, 0.45, 2.73, 7.25, 0.24, ["Simulated [12] with real-world noise and strip spread. 99.3% of real tests pass."], size=10, color=C["muted"], label="sim note")

    # native chart: a 0.50 mg/L sample read across pH
    alpha = lambda ph: 1 / (1 + 10 ** (ph - RES["pka_25C"]))
    bare85 = next(r["bare_ph7cal"] for r in RES["ph"] if abs(r["ph"] - 8.5) < 1e-9)
    ratio = bare85 / 0.5
    box(s, 0.45, 3.04, 7.25, 2.72)
    tb(s, 0.62, 3.12, 6.9, 0.3, ["The same 0.50 mg/L water, read at different pH (simulated)"], size=12.5, bold=True,
       color=C["ink"], label="ph title")
    tb(s, 0.62, 3.39, 6.9, 0.44, [[("At pH 8.5 a bare electrode set at pH 7 shows only ", {}),
                                   (f"{ratio * 100:.0f}% of the chlorine", {"bold": True, "color": C["high"]}),
                                   (". The buffered strip still reads 0.50.", {})]], size=11, color=C["body"],
       label="ph note")
    cd = XyChartData()
    s1 = cd.add_series("JalSatya strip, buffered")
    s2 = cd.add_series("Bare electrode set at pH 7")
    for r in RES["ph"]:
        s1.add_data_point(r["ph"], r["buffered"])
        s2.add_data_point(r["ph"], r["bare_ph7cal"])
    gf = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS, I(0.55), I(3.82), I(7.05), I(1.92), cd)
    ch = gf.chart
    chart_style(ch)
    for ser, col, wd in zip(ch.series, (C["ink"], C["high"]), (3.0, 2.25)):
        ser.format.line.color.rgb = rgb(col); ser.format.line.width = Pt(wd); ser.smooth = True
    axis_style(ch.value_axis, "Reading (mg/L)", grid=True, minimum=0, maximum=0.7, major=0.2, fmt="0.0")
    axis_style(ch.category_axis, "pH of the water", minimum=6, maximum=9, major=0.5, fmt="0.0")

    # policy fit
    box(s, 0.45, 5.88, 7.25, 0.97, fill=C["tap_l"], line=None)
    tb(s, 0.65, 5.95, 6.9, 0.85, [
        [("Fits rules already in force. ", {"bold": True, "color": C["ink"]}),
         ("The JJM framework allows instruments like a chlorimeter and asks for an FTK inventory with "
          "reagent expiry dates [1, Sec 4.3]. JalSatya is a strip chlorimeter that keeps its own inventory.", {})]],
       size=11.5, lnspc=1.0, anchor="m", label="policy")

    # challenges and strategies
    pointer(s, 7.95, 1.24, 4.9, "Potential challenges and risks")
    pointer(s, 7.95, 1.48, 4.9, "Strategies for overcoming these challenges", color=C["safe"])
    rows = [("Chloramine or manganese", "Low working potential; lab checks with IS 3025 and DPD [13]"),
            ("Strip spread, heat and humidity", "Batch calibration code; dry strip sealed in a foil pouch"),
            ("Wrong water or tampered reader", "Twin flags misfit readings; secure key chip; every fake burns a strip"),
            ("Testers new to a device", "One button, Hindi voice prompts, the same trained women"),
            ("Cost at national scale", "Target under Rs 10 a strip at volume, under Rs 2,500 a reader (our estimate)")]
    y = 1.84
    for risk, fix in rows:
        box(s, 7.95, y, 4.93, 0.64)
        tb(s, 8.08, y + 0.05, 1.62, 0.54, [risk], size=11, bold=True, color=C["body"], lnspc=0.92, anchor="m",
           label="risk")
        tb(s, 9.82, y + 0.05, 2.96, 0.54, [fix], size=11, color=C["safe"], lnspc=0.92, anchor="m", label="fix")
        y += 0.71
    # roadmap
    box(s, 7.95, 5.47, 4.93, 1.38, fill=C["soft"], line=None)
    tb(s, 8.12, 5.55, 4.6, 0.28, ["Roadmap"], size=12.5, bold=True, color=C["ink"], label="roadmap")
    phases = [("Today", "App, reader logic, physics model, twin, dashboard"),
              ("Finale", "Working strip and reader, checked against DPD"),
              ("Pilot", "One block with a state water department")]
    x = 8.12
    for h, t in phases:
        tb(s, x, 5.86, 1.5, 0.95, [[(h, {"bold": True, "color": C["tap"], "size": 12})], t], size=10.5, lnspc=0.95,
           label="phase")
        x += 1.6
    arrow(s, 8.72, 5.97, 9.62, 5.97); arrow(s, 10.37, 5.97, 11.22, 5.97)


# ----------------------------------------------------------------------------------------------- slide 5
def slide5(s):
    clear_content(s)
    set_title(s, "IMPACT AND BENEFITS")
    subtitle(s, "For 24.80 lakh testers, every pump operator and 15.72 crore homes on tap water")
    pointer(s, 0.45, 1.24, 7.2, "Potential impact on the target audience")

    box(s, 0.45, 1.56, 7.25, 4.06)
    tb(s, 0.62, 1.64, 6.9, 0.3, ["Village chlorine twin on a sample scheme of 120 taps (simulated)"], size=12.5,
       bold=True, color=C["ink"], label="twin title")
    tb(s, 0.62, 1.92, 6.9, 0.24, [[("Each dot is a household tap.  ", {"color": C["muted"]}),
                                   ("Red", {"bold": True, "color": C["low"]}), (" below 0.2 mg/L,  ", {}),
                                   ("green", {"bold": True, "color": C["safe"]}), (" 0.2 to 1.0,  ", {}),
                                   ("amber", {"bold": True, "color": C["high"]}), (" above 1.0 [4]", {})]],
       size=10.5, label="legend")
    pw = 3.12
    _, _, h1 = picture(s, IMG / "twin_before_eq.png", 0.74, 2.2, w=pw)
    picture(s, IMG / "twin_after_eq.png", 0.74 + pw + 0.27, 2.2, w=pw)
    cy = 2.2 + h1 + 0.07
    tb(s, 0.74, cy, pw, 0.5, [[(f"Usual dose {TWIN['habit']:.2f} mg/L", {"bold": True, "color": C["ink"]})],
                             [(f"{TWIN['before']} of 120 taps safe. ", {}),
                              (f"Far end {TWIN['tail_before']:.2f} mg/L", {"color": C["low"], "bold": True})]],
       size=11, lnspc=0.98, label="cap before")
    tb(s, 0.74 + pw + 0.27, cy, pw, 0.5, [[(f"Twin's dose {TWIN['rec']:.2f} mg/L", {"bold": True, "color": C["ink"]})],
                                         [(f"{TWIN['after']} of 120 taps safe. ", {}),
                                          (f"Far end {TWIN['tail_after']:.2f} mg/L",
                                           {"color": C["safe"], "bold": True})]],
       size=11, lnspc=0.98, label="cap after")

    who = [("Village testers", "A 10-second test, no colour to judge, Hindi voice"),
           ("Pump operators", "The exact dose to add, and an alert when a far tap runs low"),
           ("Block and district", "Only verified tests, with kit stock and expiry tracked"),
           ("DDWS and NJJM", "WQMIS numbers that stand up to audit")]
    y = 1.56
    for h, t in who:
        box(s, 7.95, y, 4.93, 0.6)
        tb(s, 8.1, y + 0.05, 1.62, 0.5, [h], size=12, bold=True, color=C["ink"], anchor="m", label="who")
        tb(s, 9.78, y + 0.05, 3.0, 0.5, [t], size=11, color=C["body"], anchor="m", lnspc=0.95, label="who t")
        y += 0.67

    pointer(s, 7.95, 4.33, 4.93, "Benefits of the solution (social, economic, environmental, etc.)", size=10.5)
    ben = [("Social", "safe chlorine at the far end of every line"),
           ("Economic", "no dye reagent to buy or throw away"),
           ("Environmental", "no o-tolidine, no liquid waste in villages"),
           ("Governance", "test counts that match strips issued")]
    y = 4.64
    for h, t in ben:
        tb(s, 7.95, y, 4.93, 0.28, [[(h + "  ", {"bold": True, "color": C["tap"]}), (t, {})]], size=11.5,
           label="benefit")
        y += 0.31

    nums = [("≥1.2 crore", "tests a year: 2 tail ends × 5.07 lakh villages × 12"),
            ("24.80 lakh", "women already trained to test with field kits [3]"),
            ("5.07 lakh", "villages where those trained testers work [3]")]
    x = 0.45
    for big, small in nums:
        number_block(s, x, 5.74, 2.35, 1.11, big, small, big_size=24)
        x += 2.45

    box(s, 7.95, 5.93, 4.93, 0.92, fill=C["ink"], line=None)
    tb(s, 8.12, 5.99, 4.62, 0.8, [[("Larger vision. ", {"bold": True, "color": "FFFFFF"}),
                                    ("pH, fluoride and nitrate strips on the same reader, a live national chlorine map, "
                                     "and links to JJM tank sensors. States buy readers once and strips from WQMS "
                                     "funds.", {"color": "D6E2F0"})]], size=10.5, lnspc=0.98, anchor="m", label="vision")


# ----------------------------------------------------------------------------------------------- slide 6
def slide6(s):
    clear_content(s)
    set_title(s, "RESEARCH AND REFERENCES")
    subtitle(s, "Every claim here traces to a public source or to our simulation")
    pointer(s, 0.45, 1.24, 7.2, "Details / Links of the reference and research work")
    refs = [
        ("Problem and policy", [
            ("[1] DDWS, Ministry of Jal Shakti, Drinking Water Quality Monitoring and Surveillance Framework, 2021",
             "jaljeevanmission.gov.in", "https://jaljeevanmission.gov.in/sites/default/files/guideline/WQMS-Framework.pdf"),
            ("[2] CAG, Performance Audit on Jal Jeevan Mission (Maharashtra), Report No. 2 of 2026, Chapter V",
             "cag.gov.in", "https://cag.gov.in/uploads/download_audit_report/2026/11.-Chapter-V-06a50a96b57bf36.83560813.pdf"),
            ("[3] PIB, Jal Jeevan Mission factsheet, data as on 21 and 22 October 2025", "pib.gov.in",
             "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/oct/doc20251026676401.pdf"),
            ("[4] BIS, IS 10500:2012, Drinking Water Specification (free residual chlorine 0.2 to 1 mg/L)",
             "consumerhelpline.gov.in", "https://consumerhelpline.gov.in/public/assets/docs/bis/IS10500-2012.pdf"),
            ("[5] Raj and Jamwal, How reliable are water quality monitoring results from field test kits, Down To "
             "Earth, Dec 2022", "downtoearth.org.in",
             "https://www.downtoearth.org.in/blog/water/how-reliable-are-water-quality-monitoring-results-from-field-test-kits-86372")]),
        ("Existing approaches", [
            ("[6] Gonz\u00e1lez G\u00f3mez et al., Color QR Codes for Smartphone-Based Analysis of Free Chlorine in "
             "Drinking Water, Sensors, 2025", "doi:10.3390/s25113251", "https://doi.org/10.3390/s25113251"),
            ("[7] Palintest ChloroSense, reagent-free electrochemical chlorine meter, 2008", "wateronline.com",
             "https://www.wateronline.com/doc/palintest-simplifies-water-testing-wth-chloro-0001"),
            ("[8] Impact of gate electrode on free chlorine sensing performance in solution-gated graphene field-effect "
             "transistors, RSC Advances, 2024", "doi:10.1039/D3RA07692J", "https://doi.org/10.1039/D3RA07692J"),
            ("[9] Shekhar et al., A Disposable Microsensor for Continuous Monitoring of Free Chlorine in Water, IEEE "
             "Sensors, 2003", "pure.korea.ac.kr",
             "https://pure.korea.ac.kr/en/publications/a-disposable-microsensor-for-continuous-monitoring-of-free-chlori/")]),
        ("Science and test methods we build on", [
            ("[10] Bard and Faulkner, Electrochemical Methods, 2nd ed., Wiley, 2001 (Cottrell equation)", None, None),
            ("[11] Morris, J. C., The acid ionization constant of HOCl from 5 to 35 \u00b0C, J. Phys. Chem. 70, 3798, 1966",
             None, None),
            ("[12] Team PARAKRAM, JalSatya simulation and demo", LINKS["code"], URLS["code"]),
            ("[13] BIS, IS 3025 (Part 26), Methods of Sampling and Test for Water and Wastewater: Chlorine, Residual",
             None, None)]),
    ]
    y = 1.56
    for head, items in refs:
        tb(s, 0.45, y, 7.3, 0.27, [head], size=12, bold=True, color=C["tap"], label="ref head")
        y += 0.28
        for text, lab, url in items:
            runs = [(text + (". " if lab else ""), {})] + ([(lab, {"color": C["tap"], "link": url})] if lab else [])
            n = lines_needed(runs, 7.3, 9.5, F, False)
            lh = bump(9.5) * 1.2 * 0.95 / 72
            tb(s, 0.45, y, 7.3, lh * n + 0.03, [runs], size=9.5, color=C["body"], lnspc=0.95, label="ref")
            y += lh * n + 0.045
        y += 0.07
    if y > 6.3:
        WARN.append(f"slide6 references end at {y:.2f}")
    pass

    box(s, 7.95, 1.56, 4.93, 2.86)
    tb(s, 8.12, 1.65, 4.6, 0.3, ["What exists, and what is new"], size=13, bold=True, color=C["ink"], label="ex head")
    rows = [("DPD and OTO colour kits [5]", "judged by eye; reagents expire"),
            ("Phone colour apps [6]", "qualitative, sensitive to light"),
            ("Electrochemical meters [7, 8, 9]", "precise, but costly and no audit trail"),
            ("JalSatya", "serialised, signed strip, plus dose advice for the village")]
    y = 2.02
    for i, (h, t) in enumerate(rows):
        last = i == len(rows) - 1
        if last:
            box(s, 8.02, y - 0.04, 4.79, 0.6, fill=C["safe_l"], line=None)
        tb(s, 8.12, y, 1.85, 0.52, [h], size=11.5, bold=True, color=C["ink"] if last else C["body"], anchor="m",
           lnspc=0.92, label="ex h")
        tb(s, 10.02, y, 2.75, 0.52, [t], size=11, bold=last, color=C["safe"] if last else C["muted"], anchor="m",
           lnspc=0.95, label="ex t")
        y += 0.6

    box(s, 7.95, 4.56, 4.93, 1.34, fill=C["soft"], line=None)
    tb(s, 8.12, 4.64, 4.6, 0.3, ["See it run"], size=13, bold=True, color=C["ink"], label="links head")
    tb(s, 8.12, 4.98, 4.7, 0.86, [[("Demo  ", {"bold": True}), (LINKS["demo"], {"color": C["tap"], "link": URLS["demo"]})],
                                 [("Code  ", {"bold": True}), (LINKS["code"], {"color": C["tap"], "link": URLS["code"]})],
                                 [("Video  ", {"bold": True}), (LINKS["video"], {"color": C["tap"], "link": URLS["video"]})]],
       size=11.5, lnspc=1.0, after=2, label="links")
    box(s, 7.95, 6.04, 4.93, 0.81, fill=C["ink"], line=None)
    tb(s, 8.12, 6.08, 4.62, 0.73, [[("JalSatya by Team PARAKRAM", {"bold": True, "color": "FFFFFF", "size": 15})],
                                   [(TAGLINE, {"color": "D6E2F0", "size": 14})]],
       font=FC, anchor="m", lnspc=0.95, label="close")


def equalise_twin_images():
    """Pad both twin screenshots to the same height so the before and after maps line up."""
    a, b = Image.open(IMG / "twin_before.png").convert("RGB"), Image.open(IMG / "twin_after.png").convert("RGB")
    H = max(a.size[1], b.size[1])
    for im, name in ((a, "twin_before_eq.png"), (b, "twin_after_eq.png")):
        if im.size[1] < H:
            bg = im.getpixel((6, im.size[1] - 6))
            canvas = Image.new("RGB", (im.size[0], H), bg)
            canvas.paste(im, (0, 0))
            im = canvas
        im.save(IMG / name)


def number_font(s):
    """Set the slide number (a field) in Barlow so it matches the deck instead of a fallback font."""
    for shp in s.placeholders:
        if "SLIDE_NUMBER" not in str(shp.placeholder_format.type):
            continue
        for el in shp._element.iter(qn("a:fld"), qn("a:r")):
            rpr = el.find(qn("a:rPr"))
            if rpr is None:
                rpr = el.makeelement(qn("a:rPr"), {"lang": "en-IN"})
                el.insert(0, rpr)
            for old in rpr.findall(qn("a:latin")):
                rpr.remove(old)
            rpr.set("b", "1"); rpr.set("sz", "1400")
            latin = rpr.makeelement(qn("a:latin"), {"typeface": F})
            # schema order inside rPr: fills and effects first, then latin, ea, cs, sym, hyperlinks, extLst
            later = [c for c in rpr if c.tag in {qn(t) for t in ("a:ea", "a:cs", "a:sym", "a:hlinkClick",
                                                                  "a:hlinkMouseOver", "a:rtl", "a:extLst")}]
            if later:
                later[0].addprevious(latin)
            else:
                rpr.append(latin)


def clean_package(prs):
    """Give the file its own identity: properties, empty speaker notes, no links left over from the template."""
    cp = prs.core_properties
    cp.title = "JalSatya: SIH26253 idea submission, Team PARAKRAM"
    cp.subject = "Strip-based free residual chlorine test kit with proof of every test"
    cp.keywords = "free residual chlorine, FRC, test strip, Jal Jeevan Mission, SIH26253"
    cp.author = "Team PARAKRAM"
    cp.last_modified_by = "Team PARAKRAM"
    cp.comments = ""
    cp.category = "Smart India Hackathon 2026"
    for sl in prs.slides:
        if sl.has_notes_slide:
            sl.notes_slide.notes_text_frame.text = ""
        used = set()
        for el in sl._element.iter():
            for k, v in el.attrib.items():
                if k.endswith("}id") or k.endswith("}embed") or k.endswith("}link"):
                    used.add(v)
        for rid, rel in list(sl.part.rels.items()):
            if rel.reltype.endswith("/hyperlink") and rid not in used:
                sl.part.drop_rel(rid)


def build():
    equalise_twin_images()
    prs = Presentation(str(TEMPLATE))
    sl = prs.slides
    slide1(sl[0]); slide2(sl[1]); slide3(sl[2]); slide4(sl[3]); slide5(sl[4]); slide6(sl[5])
    for s in list(sl)[1:6]:
        number_font(s)
    clean_package(prs)
    while len(prs.slides) > 6:
        rid = prs.slides._sldIdLst[-1].rId
        prs.part.drop_rel(rid); del prs.slides._sldIdLst[-1]
    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
    print("\n".join(WARN) if WARN else "fit check: all text boxes fit")
