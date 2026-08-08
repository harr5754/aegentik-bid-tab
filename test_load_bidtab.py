"""
Test loader for Bid Tab Prototype
Usage:
    python test_load_bidtab.py "C:\path\to\Bid Tab Prototype Rev B.xlsx"
"""

import sys
import json
from pathlib import Path
from utils.excel_loader import load_bidtab


def main():
    if len(sys.argv) < 2:
        print('Usage: python test_load_bidtab.py "C:\\path\\to\\file.xlsx"')
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    print(f"Loading: {path.name}")
    print("-" * 60)

    result = load_bidtab(str(path))

    print(f"Package name   : {result.package_name}")
    print(f"Bidders found  : {len(result.bidders)}")
    print(f"Component order: {result.component_order}")
    print(f"Notes          : {result.analysis_notes}")
    print()

    for bid in result.ranked_by_total():
        print(f"  {bid.bidder_name}")
        print(f"    Total: ${bid.total:,.0f}" if bid.total is not None else "    Total: —")
        for c in bid.components:
            print(f"      - {c.name}: ${c.amount:,.0f}")
        print()

    print("-" * 60)
    print("Raw JSON (truncated):")
    print(json.dumps(result.model_dump(), indent=2, default=str)[:3000])


if __name__ == "__main__":
    main()