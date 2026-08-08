"""
Load an EPC-style bid tab (columns = bidders, rows = cost components)
into BidTabResult.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
import math

from models.bidtab import BidComponent, BidderBid, BidTabResult


def _clean_number(val) -> Optional[float]:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        s = str(val).replace(",", "").replace("$", "").strip()
        if s == "" or s.lower() in ("nan", "none", "-"):
            return None
        return float(s)
    except Exception:
        return None


def _clean_str(val) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    return str(val).replace("\n", " ").strip()


def load_epc_bidtab(file_path: str, package_name: Optional[str] = None) -> BidTabResult:
    path = Path(file_path)
    df = pd.read_excel(path, header=None, engine="openpyxl")
    df = df.fillna("")

    # -------------------------------------------------
    # 1. Find the bidder header row
    # -------------------------------------------------
    bidder_row_idx = None
    bidder_names = []
    bidder_col_map = {}  # col_index -> bidder_name

    for i in range(min(20, len(df))):
        row_vals = [_clean_str(v).upper() for v in df.iloc[i].tolist()]
        if any(v == "BIDDERS" for v in row_vals):
            bidder_row_idx = i
            for col_idx, val in enumerate(df.iloc[i].tolist()):
                name = _clean_str(val)
                if name and name.upper() not in ("BIDDERS", "RFP DATA", "AWARD RECOMMENDATION", ""):
                    bidder_names.append(name)
                    bidder_col_map[col_idx] = name
            break

    # Fallback: look for a repeated name row (row 13 style)
    if not bidder_names:
        for i in range(min(25, len(df))):
            row_vals = [_clean_str(v) for v in df.iloc[i].tolist()]
            # Heuristic: row with 3+ non-empty text cells and few numbers
            text_cells = [v for v in row_vals if v and _clean_number(v) is None]
            if len(text_cells) >= 3:
                for col_idx, val in enumerate(row_vals):
                    if val and _clean_number(val) is None and val.upper() not in ("BIDDERS", ""):
                        if val not in bidder_names:
                            bidder_names.append(val)
                            bidder_col_map[col_idx] = val
                if len(bidder_names) >= 2:
                    bidder_row_idx = i
                    break

    if not bidder_names:
        raise ValueError("Could not find bidder names in the spreadsheet")

    # -------------------------------------------------
    # 2. Extract component rows (after bidder header)
    # -------------------------------------------------
    start_row = (bidder_row_idx or 0) + 1
    # Skip contact/address rows — look for first row that has a component-like name
    # and at least one numeric value in bidder columns
    component_order = []
    bidder_components: Dict[str, List[BidComponent]] = {name: [] for name in bidder_names}

    skip_keywords = {
        "address", "city", "contact", "phone", "email", "approvals",
        "originating", "project controls", "construction manager",
        "date", "rfp issue", "number of bcm", "original closing",
        "final closing", "evaluation prepared", "award recommendation",
        "jacobs budget", "recommended award", "recommend award",
    }

    for i in range(start_row, len(df)):
        row = df.iloc[i].tolist()
        col0 = _clean_str(row[0]) if len(row) > 0 else ""
        col1 = _clean_str(row[1]) if len(row) > 1 else ""

        # Component name is usually in column 1; sometimes only in column 0
        component_name = col1 if col1 else col0
        if not component_name:
            continue

        lower = component_name.lower()
        if any(k in lower for k in skip_keywords):
            continue

        # Must have at least one numeric amount in bidder columns
        amounts_found = False
        for col_idx, bidder_name in bidder_col_map.items():
            if col_idx >= len(row):
                continue
            amount = _clean_number(row[col_idx])
            if amount is not None:
                amounts_found = True
                break

        if not amounts_found:
            continue

        # Skip pure total rows for the stack chart (we still want line items)
        # but keep them out of component_order if they are summary totals
        is_total = lower.startswith("total") or "evaluated cost" in lower

        if component_name not in component_order and not is_total:
            component_order.append(component_name)

        for col_idx, bidder_name in bidder_col_map.items():
            if col_idx >= len(row):
                continue
            amount = _clean_number(row[col_idx])
            if amount is None:
                continue
            if is_total:
                continue  # totals handled separately if needed
            bidder_components[bidder_name].append(
                BidComponent(name=component_name, amount=amount, category=col0 or None)
            )

    # -------------------------------------------------
    # 3. Build BidTabResult
    # -------------------------------------------------
    bidders = []
    for name in bidder_names:
        comps = bidder_components.get(name, [])
        if not comps:
            continue
        bid = BidderBid(bidder_name=name, components=comps)
        bid.compute_total()
        bidders.append(bid)

    result = BidTabResult(
        package_name=package_name or path.stem,
        bidders=bidders,
        component_order=component_order,
        analysis_notes=[
            f"Loaded EPC-style bid tab with {len(bidders)} bidders",
            f"Components: {', '.join(component_order[:8])}{'...' if len(component_order) > 8 else ''}",
        ],
    )
    return result


def load_bidtab(file_path: str, package_name: Optional[str] = None) -> BidTabResult:
    """Main entry point — currently optimized for EPC column-bidder layout."""
    return load_epc_bidtab(file_path, package_name)