"""
Step 5 — Legal & Environmental Flag Mapping

Maps spatial validation results and risk scores to specific
Karnataka legal acts, environmental regulations, and revenue
rules.  Each flag includes:
  - flag_code, severity level
  - Act name / section / clause citation
  - Plain-text description
"""
import logging
from typing import Optional

from app.services.spatial_validation import SpatialValidationScore

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━  Flag Rule Database  ━━━━━━━━━━━━━━━
FLAG_RULES = [
    # ── Water bodies ──────────────────────────────────
    {
        "layer": "water_bodies",
        "check": "intersects",
        "flag_code": "WATERBODY_ENCROACHMENT",
        "flag_category": "environmental",
        "flag_label": "Water Body Encroachment",
        "severity": "critical",
        "act_name": "Karnataka Lake Conservation and Development Authority Act, 2014",
        "act_section": "Section 4 & 5",
        "clause_summary": "No person shall encroach upon, or build any structure on, "
                          "any lake, tank, or water body in Karnataka. Violations may "
                          "attract demolition orders and criminal prosecution.",
        "description_template": "The parcel directly overlaps with a water body "
                                "({overlap_pct:.1f}% overlap). This constitutes encroachment "
                                "under the Karnataka Lake Conservation Act, 2014.",
    },
    {
        "layer": "water_bodies",
        "check": "buffer",
        "flag_code": "WATERBODY_BUFFER_VIOLATION",
        "flag_category": "environmental",
        "flag_label": "Water Body Buffer Zone Violation",
        "severity": "high",
        "act_name": "Karnataka Town and Country Planning Act, 1961",
        "act_section": "Section 14A (Buffer Zone Regulations)",
        "clause_summary": "Construction within 75m (minor) / 200m (major) of a water body "
                          "is restricted. Requires special clearance from Lake Development Authority.",
        "description_template": "The parcel is within {nearest_dist_m:.0f}m of a water body. "
                                "Karnataka mandates a minimum buffer zone of {buffer_m}m. "
                                "Construction may require special clearance.",
    },

    # ── Forest areas ──────────────────────────────────
    {
        "layer": "forest_areas",
        "check": "intersects",
        "flag_code": "FOREST_ENCROACHMENT",
        "flag_category": "environmental",
        "flag_label": "Forest Land Encroachment",
        "severity": "critical",
        "act_name": "Indian Forest Act, 1927 & Karnataka Forest Act, 1963",
        "act_section": "Section 26 (IFA) / Section 41 (KFA)",
        "clause_summary": "Unauthorized occupation or clearing of forest land is a criminal "
                          "offence punishable with imprisonment up to 2 years and fine.",
        "description_template": "The parcel overlaps with designated forest land "
                                "({overlap_pct:.1f}% overlap). This constitutes encroachment under "
                                "the Indian Forest Act and Karnataka Forest Act.",
    },
    {
        "layer": "forest_areas",
        "check": "buffer",
        "flag_code": "FOREST_PROXIMITY",
        "flag_category": "environmental",
        "flag_label": "Proximity to Forest Land",
        "severity": "medium",
        "act_name": "Forest Conservation Act, 1980",
        "act_section": "Section 2",
        "clause_summary": "Development near forest land requires prior approval from "
                          "the Central Government. Activities within the forest fringe "
                          "may require Environmental Impact Assessment.",
        "description_template": "The parcel is within {nearest_dist_m:.0f}m of forest land. "
                                "Construction near forest boundaries may require Forest "
                                "Conservation Act clearance.",
    },

    # ── Eco-sensitive zones ───────────────────────────
    {
        "layer": "eco_sensitive_zones",
        "check": "intersects",
        "flag_code": "ESZ_VIOLATION",
        "flag_category": "environmental",
        "flag_label": "Eco-Sensitive Zone Violation",
        "severity": "critical",
        "act_name": "Environment Protection Act, 1986 (ESZ Notification)",
        "act_section": "MoEFCC Notification S.O. 1533(E)",
        "clause_summary": "Construction and commercial activities within notified "
                          "Eco-Sensitive Zones are prohibited or heavily restricted. "
                          "Violators face penalties under the Environment Protection Act.",
        "description_template": "The parcel falls within a notified Eco-Sensitive Zone "
                                "({overlap_pct:.1f}% overlap). Construction is prohibited "
                                "or requires MoEFCC clearance.",
    },
    {
        "layer": "eco_sensitive_zones",
        "check": "buffer",
        "flag_code": "ESZ_PROXIMITY",
        "flag_category": "environmental",
        "flag_label": "Near Eco-Sensitive Zone",
        "severity": "high",
        "act_name": "Environment Protection Act, 1986",
        "act_section": "Eco-Sensitive Zone Guidelines",
        "clause_summary": "Development adjacent to Eco-Sensitive Zones is subject to "
                          "heightened scrutiny and may require Environmental Impact Assessment.",
        "description_template": "The parcel is within {nearest_dist_m:.0f}m of an Eco-Sensitive Zone. "
                                "Development in this proximity requires environmental clearance.",
    },

    # ── Flood zones ───────────────────────────────────
    {
        "layer": "flood_zones",
        "check": "intersects",
        "flag_code": "FLOOD_ZONE_RISK",
        "flag_category": "environmental",
        "flag_label": "Flood-Prone Area",
        "severity": "high",
        "act_name": "Karnataka Disaster Management Act & National Flood Policy",
        "act_section": "District Flood Zoning Regulations",
        "clause_summary": "Construction in flood-prone zones must comply with flood-resistant "
                          "building codes. Certain flood plains are restricted for development.",
        "description_template": "The parcel is in a designated flood-prone zone "
                                "({overlap_pct:.1f}% overlap). Construction must comply with "
                                "flood-resistant building codes.",
    },

    # ── Government land ───────────────────────────────
    {
        "layer": "govt_land",
        "check": "intersects",
        "flag_code": "GOVT_LAND_CONFLICT",
        "flag_category": "legal",
        "flag_label": "Government Land Conflict",
        "severity": "critical",
        "act_name": "Karnataka Land Revenue Act, 1964",
        "act_section": "Section 67 & 76A",
        "clause_summary": "Government land (A-kharab, B-kharab, gomala) cannot be sold, "
                          "purchased, or developed by private parties. Unauthorized occupation "
                          "attracts eviction proceedings and penalties.",
        "description_template": "The parcel overlaps with government-classified land "
                                "({overlap_pct:.1f}% overlap). Private development on government "
                                "land is prohibited under the Karnataka Land Revenue Act.",
    },
]


class FlagResult:
    """One raised legal/environmental flag."""
    def __init__(
        self,
        flag_code: str,
        flag_category: str,
        flag_label: str,
        description: str,
        severity: str,
        act_name: str,
        act_section: str,
        clause_summary: str,
        layer_name: str,
        overlap_pct: float,
        nearest_dist_m: Optional[float],
    ):
        self.flag_code = flag_code
        self.flag_category = flag_category
        self.flag_label = flag_label
        self.description = description
        self.severity = severity
        self.act_name = act_name
        self.act_section = act_section
        self.clause_summary = clause_summary
        self.layer_name = layer_name
        self.overlap_pct = overlap_pct
        self.nearest_dist_m = nearest_dist_m


class FlagMappingService:
    """
    Evaluates spatial validation scores against the flag rule database
    and emits applicable legal / environmental flags.
    """

    def map_flags(
        self,
        validation_scores: list[SpatialValidationScore],
    ) -> list[FlagResult]:
        """Generate flags for all applicable layers."""
        flags: list[FlagResult] = []
        score_map = {s.layer_name: s for s in validation_scores}

        for rule in FLAG_RULES:
            layer_name = rule["layer"]
            score = score_map.get(layer_name)
            if score is None:
                continue

            triggered = False
            if rule["check"] == "intersects" and score.intersects:
                triggered = True
            elif rule["check"] == "buffer" and not score.intersects:
                # Trigger if within buffer distance
                if (
                    score.nearest_feature_dist_m is not None
                    and score.buffer_distance_m > 0
                    and score.nearest_feature_dist_m <= score.buffer_distance_m
                ):
                    triggered = True

            if triggered:
                desc = rule["description_template"].format(
                    overlap_pct=score.overlap_pct,
                    nearest_dist_m=score.nearest_feature_dist_m or 0,
                    buffer_m=score.buffer_distance_m,
                )
                flags.append(FlagResult(
                    flag_code=rule["flag_code"],
                    flag_category=rule["flag_category"],
                    flag_label=rule["flag_label"],
                    description=desc,
                    severity=rule["severity"],
                    act_name=rule["act_name"],
                    act_section=rule["act_section"],
                    clause_summary=rule["clause_summary"],
                    layer_name=layer_name,
                    overlap_pct=score.overlap_pct,
                    nearest_dist_m=score.nearest_feature_dist_m,
                ))

        logger.info("Raised %d legal/environmental flags", len(flags))
        return flags
