"""
Step 6 — LLM Explainability Layer

Takes the structured risk + flags data and produces:
  - A plain-language summary in English (non-technical tone)
  - Recommended next steps

Supports Gemini (Google), OpenAI, or a local fallback (template-based).
"""
import logging
from typing import Optional

import httpx

from app.config import get_settings
from app.services.risk_classifier import RiskPrediction
from app.services.flag_mapping import FlagResult
from app.services.spatial_validation import SpatialValidationScore

logger = logging.getLogger(__name__)
settings = get_settings()


class ExplainabilityResult:
    """Output of the LLM explainability layer."""
    def __init__(
        self,
        plain_language_summary: str,
        recommended_next_steps: list[str],
    ):
        self.plain_language_summary = plain_language_summary
        self.recommended_next_steps = recommended_next_steps


class LLMExplainerService:
    """
    Generates human-readable explanations for the safety report.
    """

    async def explain(
        self,
        risk: RiskPrediction,
        flags: list[FlagResult],
        validations: list[SpatialValidationScore],
        parcel_info: dict,
    ) -> ExplainabilityResult:
        """
        Produce plain-language summary & next steps.
        Tries LLM first, falls back to template-based generation.
        """
        provider = settings.LLM_PROVIDER

        if provider == "gemini" and settings.GOOGLE_API_KEY:
            return await self._explain_gemini(risk, flags, validations, parcel_info)
        elif provider == "openai" and settings.OPENAI_API_KEY:
            return await self._explain_openai(risk, flags, validations, parcel_info)
        else:
            logger.info("No LLM API key configured — using template-based explanation")
            return self._explain_template(risk, flags, validations, parcel_info)

    # ─── Gemini ───────────────────────────────────────
    async def _explain_gemini(
        self,
        risk: RiskPrediction,
        flags: list[FlagResult],
        validations: list[SpatialValidationScore],
        parcel_info: dict,
    ) -> ExplainabilityResult:
        """Generate explanation via Gemini REST API (stable fallback over SDK transport issues)."""
        try:
            prompt = self._build_prompt(risk, flags, validations, parcel_info)
            model_name = settings.LLM_MODEL or "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            params = {"key": settings.GOOGLE_API_KEY}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1200},
            }

            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(url, params=params, json=payload)
                response.raise_for_status()
                data = response.json()

            text = ""
            candidates = data.get("candidates") or []
            if candidates:
                parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
                text = "\n".join((p.get("text", "") for p in parts if isinstance(p, dict))).strip()
            if not text:
                raise ValueError("Gemini response missing text")

            summary, steps = self._parse_llm_response(text)
            if not steps:
                steps = self._explain_template(risk, flags, validations, parcel_info).recommended_next_steps

            return ExplainabilityResult(
                plain_language_summary=summary,
                recommended_next_steps=steps,
            )
        except Exception as e:
            logger.warning("Gemini API failed: %s — falling back to template", e)
            return self._explain_template(risk, flags, validations, parcel_info)

    # ─── OpenAI ───────────────────────────────────────
    async def _explain_openai(
        self,
        risk: RiskPrediction,
        flags: list[FlagResult],
        validations: list[SpatialValidationScore],
        parcel_info: dict,
    ) -> ExplainabilityResult:
        """Generate explanation via OpenAI API."""
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = self._build_prompt(risk, flags, validations, parcel_info)

            completion = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": (
                        "You are GeoSafe, an AI land safety advisor for Karnataka, India. "
                        "Explain land risk assessments in plain, non-technical English that "
                        "anyone can understand. Be specific about legal implications."
                    )},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1500,
            )

            text = completion.choices[0].message.content
            summary, steps = self._parse_llm_response(text)

            return ExplainabilityResult(
                plain_language_summary=summary,
                recommended_next_steps=steps,
            )
        except Exception as e:
            logger.warning("OpenAI API failed: %s — falling back to template", e)
            return self._explain_template(risk, flags, validations, parcel_info)

    # ─── Prompt Builder ───────────────────────────────
    @staticmethod
    def _build_prompt(
        risk: RiskPrediction,
        flags: list[FlagResult],
        validations: list[SpatialValidationScore],
        parcel_info: dict,
    ) -> str:
        location = parcel_info.get("raw_input", "Unknown location")

        flag_text = ""
        for f in flags:
            flag_text += (
                f"\n- **{f.flag_label}** (Severity: {f.severity}): "
                f"{f.description} "
                f"[{f.act_name}, {f.act_section}]"
            )

        validation_text = ""
        for v in validations:
            validation_text += (
                f"\n- {v.layer_label}: "
                f"{'Overlaps' if v.intersects else 'No overlap'}, "
                f"{v.overlap_pct:.1f}% overlap, "
                f"score={v.spatial_score:.2f}"
            )

        shap_text = ""
        for feat, val in risk.shap_values.items():
            shap_text += f"\n- {feat}: {val:.4f}"

        prompt = f"""
Analyse the following land parcel safety assessment for a property buyer in Karnataka, India.
Write a clear, easy-to-understand summary and recommend next steps.

**Location**: {location}
**Risk Level**: {risk.risk_level} (Confidence: {risk.confidence:.0%})

**Layer Analysis**:{validation_text}

**Legal/Environmental Flags Raised**:{flag_text if flag_text else "\n- None"}

**Key Risk Factors (SHAP importance)**:{shap_text}

Please provide:
1. SUMMARY: A plain-English paragraph (3-5 sentences) explaining the safety status,
   key risks, and legal implications. Avoid technical jargon.
2. NEXT_STEPS: A numbered list of 3-5 recommended actions for the buyer.

Format your response exactly as:
SUMMARY:
[your summary]

NEXT_STEPS:
1. [step 1]
2. [step 2]
...
"""
        return prompt

    @staticmethod
    def _parse_llm_response(text: str) -> tuple[str, list[str]]:
        """Parse the SUMMARY / NEXT_STEPS format from LLM output."""
        summary = ""
        steps = []

        if "SUMMARY:" in text:
            parts = text.split("SUMMARY:", 1)
            rest = parts[1]
            if "NEXT_STEPS:" in rest:
                summary_part, steps_part = rest.split("NEXT_STEPS:", 1)
                summary = summary_part.strip()
                # Parse numbered list
                for line in steps_part.strip().split("\n"):
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith("-")):
                        # Remove numbering
                        clean = line.lstrip("0123456789.-) ").strip()
                        if clean:
                            steps.append(clean)
            else:
                summary = rest.strip()
        else:
            summary = text.strip()

        return summary, steps

    # ─── Template-Based Fallback ──────────────────────
    def _explain_template(
        self,
        risk: RiskPrediction,
        flags: list[FlagResult],
        validations: list[SpatialValidationScore],
        parcel_info: dict,
    ) -> ExplainabilityResult:
        """Generate explanation without LLM — pure template."""
        location = parcel_info.get("raw_input", "the specified location")

        # Risk intro
        risk_descriptions = {
            "HIGH": (
                f"This land parcel at {location} has been classified as **HIGH RISK** "
                f"(confidence: {risk.confidence:.0%}). Our analysis has identified serious "
                f"legal and environmental concerns that could prevent development or "
                f"result in legal action."
            ),
            "MEDIUM": (
                f"This land parcel at {location} has been classified as **MEDIUM RISK** "
                f"(confidence: {risk.confidence:.0%}). While not immediately prohibited, "
                f"there are regulatory and environmental factors that require careful "
                f"investigation before proceeding."
            ),
            "LOW": (
                f"This land parcel at {location} has been classified as **LOW RISK** "
                f"(confidence: {risk.confidence:.0%}). Our analysis did not identify "
                f"major legal or environmental obstacles. However, standard due diligence "
                f"is still recommended."
            ),
        }

        summary_parts = [risk_descriptions.get(risk.risk_level, "")]

        # Add flag summaries
        critical_flags = [f for f in flags if f.severity == "critical"]
        high_flags = [f for f in flags if f.severity == "high"]

        if critical_flags:
            labels = ", ".join(f.flag_label for f in critical_flags)
            summary_parts.append(
                f"CRITICAL issues found: {labels}. These may completely "
                f"prevent legal construction or purchase."
            )

        if high_flags:
            labels = ", ".join(f.flag_label for f in high_flags)
            summary_parts.append(
                f"High-priority concerns: {labels}. These require regulatory "
                f"clearances before any development."
            )

        # Add top SHAP factor
        if risk.shap_values:
            top_factor = max(risk.shap_values.items(), key=lambda x: abs(x[1]))
            factor_labels = {
                "water_bodies": "proximity to water bodies",
                "forest_areas": "proximity to forest land",
                "eco_sensitive_zones": "location within eco-sensitive zones",
                "flood_zones": "flood risk exposure",
                "govt_land": "conflict with government land records",
            }
            factor_label = factor_labels.get(top_factor[0], top_factor[0])
            summary_parts.append(
                f"The primary risk factor is {factor_label}."
            )

        summary = " ".join(summary_parts)

        # Next steps
        steps = []
        if risk.risk_level == "HIGH":
            steps = [
                "Consult a land-use lawyer specializing in Karnataka property law before proceeding with any purchase or development.",
                "Obtain an official Encumbrance Certificate (EC) and verify all land records at the Sub-Registrar's office.",
                "Apply for clearance from the Karnataka Lake Conservation Authority if water body flags were raised.",
                "Request a formal Forest Clearance from the District Forest Officer if forest-related flags were raised.",
                "Consider alternative land parcels that do not fall within restricted or eco-sensitive zones.",
            ]
        elif risk.risk_level == "MEDIUM":
            steps = [
                "Verify land ownership and title through the Kaveri online portal (landrecords.karnataka.gov.in).",
                "Consult the local planning authority (BDA/BMRDA) about zoning and permissible land use.",
                "Obtain an Environmental Impact Assessment if the parcel is near eco-sensitive areas.",
                "Check with the local Tahsildar office for any existing encumbrances or government notifications.",
            ]
        else:
            steps = [
                "Verify land ownership through the Kaveri / Bhoomi online portal.",
                "Obtain a standard Encumbrance Certificate from the Sub-Registrar's office.",
                "Confirm the approved land-use plan with the local Town Planning Authority.",
            ]

        return ExplainabilityResult(
            plain_language_summary=summary,
            recommended_next_steps=steps,
        )
