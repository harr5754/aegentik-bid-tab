import streamlit as st
from pathlib import Path
import tempfile
import os
import plotly.graph_objects as go

from utils.excel_loader import load_bidtab
from models.bidtab import BidTabResult


st.set_page_config(
    page_title="Aegis Contracts — Graphic Bid Tab",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Aegis Contracts — Graphic Bid Tab")
st.caption("Stacked vertical bar comparison of bidder cost components")

# ------------------------------------------------------------------
# Color palette for components (consistent across bars)
# ------------------------------------------------------------------
COMPONENT_COLORS = [
    "#2563eb",  # blue
    "#16a34a",  # green
    "#ca8a04",  # amber
    "#dc2626",  # red
    "#7c3aed",  # violet
    "#0891b2",  # cyan
    "#ea580c",  # orange
    "#4b5563",  # gray
    "#db2777",  # pink
    "#65a30d",  # lime
]


def build_stacked_chart(result: BidTabResult) -> go.Figure:
    """
    One vertical bar per bidder; components stacked by color.
    """
    ranked = result.ranked_by_total()
    bidder_names = [b.bidder_name for b in ranked]
    component_order = result.component_order or []

    # Build amount lookup: bidder -> {component: amount}
    amounts = {}
    for b in ranked:
        amounts[b.bidder_name] = {c.name: c.amount for c in b.components}

    fig = go.Figure()

    for i, comp in enumerate(component_order):
        y_values = [amounts.get(name, {}).get(comp, 0) or 0 for name in bidder_names]
        # Skip all-zero components to keep chart clean
        if sum(y_values) == 0:
            continue
        fig.add_trace(go.Bar(
            name=comp,
            x=bidder_names,
            y=y_values,
            marker_color=COMPONENT_COLORS[i % len(COMPONENT_COLORS)],
            hovertemplate=f"<b>{comp}</b><br>%{{x}}: $%{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        title=result.package_name or "Bid Comparison",
        xaxis_title="Bidder",
        yaxis_title="Amount (USD)",
        yaxis_tickformat="$,.0f",
        legend_title="Cost Component",
        height=520,
        margin=dict(l=40, r=40, t=60, b=80),
        hovermode="x unified",
    )
    return fig


# ------------------------------------------------------------------
# Upload
# ------------------------------------------------------------------
uploaded = st.file_uploader(
    "Upload Bid Tab Excel (.xlsx)",
    type=["xlsx", "xls"],
    help="EPC-style bid tab: columns = bidders, rows = cost components"
)

if uploaded is not None:
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name

    try:
        with st.spinner("Parsing bid tab..."):
            result = load_bidtab(tmp_path, package_name=Path(uploaded.name).stem)

        if not result.bidders:
            st.error("No bidders with cost data were found in this file.")
            st.stop()

        # -------------------- Summary metrics --------------------
        ranked = result.ranked_by_total()
        lowest = ranked[0]
        highest = ranked[-1]

        st.subheader(result.package_name or "Bid Tab Analysis")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Bidders", len(ranked))
        m2.metric("Lowest Bid", f"${lowest.total:,.0f}", lowest.bidder_name)
        m3.metric("Highest Bid", f"${highest.total:,.0f}", highest.bidder_name)
        spread = ((highest.total - lowest.total) / lowest.total * 100) if lowest.total else 0
        m4.metric("Spread", f"{spread:.0f}%")

        # -------------------- Chart --------------------
        st.subheader("Component Breakdown by Bidder")
        fig = build_stacked_chart(result)
        st.plotly_chart(fig, use_container_width=True)

        # -------------------- Ranking table --------------------
        st.subheader("Bid Ranking")
        table_rows = []
        for i, b in enumerate(ranked, 1):
            table_rows.append({
                "Rank": i,
                "Bidder": b.bidder_name,
                "Total": b.total,
                "vs Lowest": f"+${b.total - lowest.total:,.0f}" if i > 1 else "—",
                "vs Lowest %": f"+{((b.total - lowest.total) / lowest.total * 100):.1f}%" if i > 1 and lowest.total else "—",
            })
        st.dataframe(
            table_rows,
            use_container_width=True,
            column_config={
                "Total": st.column_config.NumberColumn(format="$%.0f"),
            },
            hide_index=True,
        )

        # -------------------- Component detail table --------------------
        with st.expander("Full component matrix"):
            # Build matrix: rows = components, columns = bidders
            import pandas as pd
            data = {"Component": result.component_order}
            for b in ranked:
                lookup = {c.name: c.amount for c in b.components}
                data[b.bidder_name] = [lookup.get(comp, None) for comp in result.component_order]
            matrix = pd.DataFrame(data)
            st.dataframe(
                matrix,
                use_container_width=True,
                column_config={
                    col: st.column_config.NumberColumn(format="$%.0f")
                    for col in matrix.columns if col != "Component"
                },
                hide_index=True,
            )

        st.success(f"Loaded {len(ranked)} bidders · {len(result.component_order)} components")

    except Exception as e:
        st.error(f"Failed to parse bid tab: {e}")
        st.exception(e)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

else:
    st.info("Upload an EPC-style bid tab Excel file to see the graphic comparison.")