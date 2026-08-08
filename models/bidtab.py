from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class BidComponent(BaseModel):
    """A single cost component within a bidder's proposal."""
    name: str
    amount: float
    category: Optional[str] = None  # e.g. Mobilization, Labor, Materials, Design


class BidderBid(BaseModel):
    """Complete bid from one contractor / supplier."""
    bidder_name: str
    components: List[BidComponent] = Field(default_factory=list)
    total: Optional[float] = None
    notes: Optional[str] = None

    def compute_total(self) -> float:
        self.total = sum(c.amount for c in self.components)
        return self.total


class BidTabResult(BaseModel):
    """Full bid tab analysis ready for charting and export."""
    package_name: Optional[str] = None
    bidders: List[BidderBid] = Field(default_factory=list)
    component_order: List[str] = Field(default_factory=list)  # consistent stack order
    currency: str = "USD"
    analysis_notes: List[str] = Field(default_factory=list)

    def ranked_by_total(self) -> List[BidderBid]:
        for b in self.bidders:
            if b.total is None:
                b.compute_total()
        return sorted(self.bidders, key=lambda b: b.total or 0)