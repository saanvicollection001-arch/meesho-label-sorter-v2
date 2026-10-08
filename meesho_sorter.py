from __future__ import annotations

import io
import re
from dataclasses import dataclass, asdict
from typing import Iterable, List, Tuple, Optional, Dict, Any

import fitz  # PyMuPDF
import pandas as pd

# User-confirmed size order.
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL", "XXXL", "4XL", "5XL", "6XL", "7XL", "8XL"]
SIZE_RANK = {size: idx for idx, size in enumerate(SIZE_ORDER)}
SIZE_ALIASES = {
    "2XL": "XXL",
    "3XL": "XXXL",
    "XXXXL": "4XL",
    "XXXXXL": "5XL",
    "XXXXXXL": "6XL",
    "XXXXXXXL": "7XL",
    "XXXXXXXXL": "8XL",
}


@dataclass
class LabelRow:
    source_file: str
    source_index: int
    page_number: int
    sku: str
    family: str
    size: str
    qty: str
    color: str
    order_no: str
    parse_status: str = "OK"
    parse_note: str = ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def normalize_size(value: str) -> str:
    value = normalize_space(value).upper()
    return SIZE_ALIASES.get(value, value)


def product_family(sku: str) -> str:
    """
    Group SKUs by removing only a trailing numeric suffix for sorting logic.

    Examples:
      RED_white_Flowar_01  -> RED_white_Flowar
      RED_white_Flowar16   -> RED_white_Flowar
      ROSE PINK_289        -> ROSE PINK
      madhuri 22           -> madhuri
      RED_white_Flowar_A   -> RED_white_Flowar_A  (text suffix stays separate)

    The original SKU printed on the PDF is never modified.
    """
    original = normalize_space(sku)
    # Remove trailing digits and any separators/punctuation immediately before them.
    # This intentionally handles variants such as:
    #   BLUSHPINK_01, BLUSHPINK-01, BLUSHPINK.01, BLUSHPINK01
    # while keeping text suffixes such as BLUSHPINK_A separate.
    base = re.sub(r"[\W_]*\d+\s*$", "", original, flags=re.UNICODE).strip()
    return base or original


def family_group_key(family: str) -> str:
    """
    Internal-only key used to decide whether two SKU families are the same product.

    Case and separators/punctuation are ignored so these group together:
      BLUSHPINK, blush pink, BLUSH_PINK, BLUSH-PINK

    Letters are never removed, so a text suffix still creates another product:
      BLUSHPINK_A != BLUSHPINK

    The PDF page and printed SKU are never changed.
    """
    value = normalize_space(family).casefold()
    return "".join(ch for ch in value if ch.isalnum())


def alpha_key(value: str):
    """Alphabetical, case-insensitive natural key."""
    parts = re.split(r"(\d+)", normalize_space(value).casefold())
    return tuple(int(part) if part.isdigit() else part for part in parts)


def _find_header_row(words):
    sku_headers = [w for w in words if normalize_space(w[4]).casefold() == "sku"]
    for sku_header in sorted(sku_headers, key=lambda w: w[1]):
        y = sku_header[1]
        row = [w for w in words if abs(w[1] - y) <= 3.0]
        tokens = {normalize_space(w[4]).casefold() for w in row}
        if {"sku", "size", "qty", "color", "order"}.issubset(tokens):
            return sku_header, row
    return None, None


def _extract_by_coordinates(page: fitz.Page) -> Optional[Tuple[str, str, str, str, str]]:
    words = page.get_text("words")
    if not words:
        return None

    sku_header, header_row = _find_header_row(words)
    if not sku_header:
        return None

    header_y = sku_header[1]

    def x_of(token: str) -> Optional[float]:
        matches = [w for w in header_row if normalize_space(w[4]).casefold() == token]
        return matches[0][0] if matches else None

    sx = x_of("sku")
    sizex = x_of("size")
    qtyx = x_of("qty")
    colorx = x_of("color")
    orderx = x_of("order")
    if any(v is None for v in (sx, sizex, qtyx, colorx, orderx)):
        return None

    candidates = [
        w for w in words
        if header_y + 4.0 < w[1] < header_y + 32.0 and w[0] >= sx - 3.0
    ]
    if not candidates:
        return None

    data_y = min(w[1] for w in candidates)
    data_row = [w for w in candidates if abs(w[1] - data_y) <= 3.0]
    bounds = [sx, sizex, qtyx, colorx, orderx, page.rect.width + 1.0]

    values = []
    for left, right in zip(bounds, bounds[1:]):
        col_words = [w for w in data_row if left - 3.0 <= w[0] < right - 3.0]
        col_words.sort(key=lambda w: w[0])
        values.append(normalize_space(" ".join(w[4] for w in col_words)))

    sku, size, qty, color, order_no = values
    if sku and size:
        return sku, size, qty, color, order_no
    return None


def _extract_by_text_fallback(page: fitz.Page) -> Optional[Tuple[str, str, str, str, str]]:
    lines = [normalize_space(line) for line in page.get_text("text").splitlines()]
    lines = [line for line in lines if line]
    for i, line in enumerate(lines):
        if line.casefold() == "order no." and i + 5 < len(lines):
            sku, size, qty, color, order_no = lines[i + 1:i + 6]
            if sku and size:
                return sku, size, qty, color, order_no
    return None


def extract_label_metadata(page: fitz.Page) -> Tuple[str, str, str, str, str, str, str]:
    result = _extract_by_coordinates(page) or _extract_by_text_fallback(page)
    if not result:
        return "", "", "", "", "", "UNREADABLE", "SKU/Size could not be detected"

    sku, raw_size, qty, color, order_no = result
    size = normalize_size(raw_size)
    if size not in SIZE_RANK:
        return sku, size, qty, color, order_no, "UNREADABLE", f"Unsupported/unknown size: {raw_size}"

    return sku, size, qty, color, order_no, "OK", ""


def analyze_pdf_bytes(named_pdf_bytes: Iterable[Tuple[str, bytes]]) -> Tuple[List[LabelRow], List[fitz.Document]]:
    rows: List[LabelRow] = []
    docs: List[fitz.Document] = []

    for source_index, (name, data) in enumerate(named_pdf_bytes):
        doc = fitz.open(stream=data, filetype="pdf")
        docs.append(doc)
        for page_index in range(doc.page_count):
            page = doc[page_index]
            sku, size, qty, color, order_no, status, note = extract_label_metadata(page)
            rows.append(
                LabelRow(
                    source_file=name,
                    source_index=source_index,
                    page_number=page_index + 1,
                    sku=sku,
                    family=product_family(sku) if sku else "",
                    size=size,
                    qty=qty,
                    color=color,
                    order_no=order_no,
                    parse_status=status,
                    parse_note=note,
                )
            )

    return rows, docs


def sort_rows(rows: List[LabelRow]) -> List[LabelRow]:
    """
    Confirmed workflow:
      1) Product family alphabetical
      2) Within family: XS,S,M,L,XL,XXL,XXXL/3XL,4XL...8XL
      3) Same family+size from all accounts stays continuous
      4) Unreadable pages go to the very end in original upload/page order
    """
    readable = [r for r in rows if r.parse_status == "OK"]
    unreadable = [r for r in rows if r.parse_status != "OK"]

    readable = sorted(
        readable,
        key=lambda r: (
            alpha_key(family_group_key(r.family)),
            SIZE_RANK[r.size],
            r.source_index,
            r.page_number,
        ),
    )
    unreadable = sorted(unreadable, key=lambda r: (r.source_index, r.page_number))
    return readable + unreadable


def build_sorted_pdf(rows: List[LabelRow], docs: List[fitz.Document]) -> Tuple[bytes, bool, int]:
    sorted_rows = sort_rows(rows)
    normal = [r for r in sorted_rows if r.parse_status == "OK"]
    errors = [r for r in sorted_rows if r.parse_status != "OK"]

    out = fitz.open()

    for row in normal:
        src = docs[row.source_index]
        p = row.page_number - 1
        out.insert_pdf(src, from_page=p, to_page=p)

    blank_inserted = False
    if errors:
        # A single blank "label-sized" separator page marks the start of error labels.
        first_error = errors[0]
        ref_page = docs[first_error.source_index][first_error.page_number - 1]
        out.new_page(width=ref_page.rect.width, height=ref_page.rect.height)
        blank_inserted = True

        for row in errors:
            src = docs[row.source_index]
            p = row.page_number - 1
            out.insert_pdf(src, from_page=p, to_page=p)

    expected_pages = len(rows) + (1 if blank_inserted else 0)
    if out.page_count != expected_pages:
        out.close()
        raise RuntimeError(f"Output page validation failed: expected {expected_pages}, got {out.page_count}")

    data = out.tobytes(garbage=3, deflate=True)
    page_count = out.page_count
    out.close()
    return data, blank_inserted, page_count


def rows_dataframe(rows: List[LabelRow]) -> pd.DataFrame:
    return pd.DataFrame([asdict(r) for r in sort_rows(rows)])


def summary_dataframe(rows: List[LabelRow]) -> pd.DataFrame:
    ok = [r for r in rows if r.parse_status == "OK"]
    if not ok:
        return pd.DataFrame(columns=["Product Family", "Size", "Labels"])

    df = pd.DataFrame([asdict(r) for r in ok])
    # Group using the same internal family normalization used for label sorting,
    # while displaying the first original family spelling.
    df["family_key"] = df["family"].map(family_group_key)
    display_names = df.groupby("family_key", sort=False)["family"].first()
    summary = (
        df.groupby(["family_key", "size"], dropna=False)
        .size()
        .reset_index(name="Labels")
    )
    summary["family"] = summary["family_key"].map(display_names)
    summary["_family"] = summary["family"].map(alpha_key)
    summary["_size"] = summary["size"].map(SIZE_RANK)
    summary = summary.sort_values(["_family", "_size"], kind="stable")
    summary = summary.drop(columns=["family_key", "_family", "_size"])
    return summary[["family", "size", "Labels"]].rename(columns={"family": "Product Family", "size": "Size"})


def process_pdfs(named_pdf_bytes: Iterable[Tuple[str, bytes]]) -> Dict[str, Any]:
    rows, docs = analyze_pdf_bytes(named_pdf_bytes)
    try:
        sorted_pdf, blank_inserted, output_pages = build_sorted_pdf(rows, docs)
        order_df = rows_dataframe(rows)
        summary_df = summary_dataframe(rows)
    finally:
        for doc in docs:
            doc.close()

    unreadable_df = order_df[order_df["parse_status"] != "OK"].copy()
    readable_df = order_df[order_df["parse_status"] == "OK"].copy()

    return {
        "rows": rows,
        "order_df": order_df,
        "summary_df": summary_df,
        "unreadable_df": unreadable_df,
        "readable_df": readable_df,
        "sorted_pdf": sorted_pdf,
        "blank_inserted": blank_inserted,
        "input_labels": len(rows),
        "output_pages": output_pages,
        "product_families": (
            int(readable_df["family"].map(family_group_key).nunique()) if len(readable_df) else 0
        ),
    }
