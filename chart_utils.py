import math


def build_donut_segments(category_totals, radius=80, stroke_width=32):
    """
    category_totals: [{'category': str, 'amount': float, 'color': str}, ...]
    Her kategori için bir SVG <circle> dash-offset segmenti üretir (donut chart).
    Döner: [{'category', 'amount', 'percent', 'color', 'dasharray', 'dashoffset'}, ...]
    """
    total = sum(c["amount"] for c in category_totals)
    if total <= 0:
        return []

    circumference = 2 * math.pi * radius
    segments = []
    offset_acc = 0.0

    for item in category_totals:
        fraction = item["amount"] / total
        arc_length = fraction * circumference
        segments.append({
            "category": item["category"],
            "amount": item["amount"],
            "percent": round(fraction * 100, 1),
            "color": item["color"],
            "dasharray": f"{arc_length:.2f} {circumference - arc_length:.2f}",
            "dashoffset": f"{-offset_acc:.2f}",
        })
        offset_acc += arc_length

    return segments
