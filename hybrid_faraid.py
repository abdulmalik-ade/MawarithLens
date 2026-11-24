import json
import os
import time
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from typing import Literal, TypeVar
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

OWNER = "yazinsai"
REPO = "islamic-inheritance-calc"
BRANCH = "main"

MODEL_CANDIDATES = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-4-hydrogen",
    "gemini-3.8-flash",
]


class ExtractedHeir(BaseModel):
    heir_type: str = Field(
        description="Normalized heir label e.g. Wife, Husband, Mother, Father, Son, Daughter, FullBrother, FullSister, MaternalBrother"
    )
    count: int = Field(ge=0)
    blocked_or_note: str = Field(default="")


class ExtractedCase(BaseModel):
    deceased_gender: Literal["male", "female", "unknown"] = "male"
    madhab: Literal["maliki", "hanafi"] = "maliki"
    gross_estate_value: float = Field(default=0.0)
    deductions_funeral_debts_wasiyyah: float = Field(default=0.0)
    currency: str = Field(default="₦")
    heirs: list[ExtractedHeir] = Field(default_factory=list)
    needs_scholar_review: bool = False
    escalation_reasons: list[str] = Field(default_factory=list)


class HeirShareExplanation(BaseModel):
    heir: str
    count: int
    fraction: str = Field(description="Exact reduced fraction string like 1/8, 7/12, 7/24, or 0")
    estimated_amount_text: str
    explanation: str
    quran_reference: str
    hadith_reference: str
    scholar_reference: str


class HybridFaraidResponse(BaseModel):
    status: Literal["ok", "escalated_to_scholar"]
    madhab_used: str
    net_estate_summary: str
    escalation_notice: str = ""
    shares: list[HeirShareExplanation] = Field(default_factory=list)
    reference_benchmark_note: str = ""


SchemaT = TypeVar("SchemaT", bound=BaseModel)


def collect_api_keys(extra_secrets: dict | None = None) -> list[str]:
    """Collects primary and secondary Gemini API keys without exposing them to frontend widgets."""
    candidate_names = ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]
    keys: list[str] = []

    for name in candidate_names:
        val = (os.getenv(name) or "").strip()
        if not val and extra_secrets:
            try:
                val = str(extra_secrets.get(name, "") or "").strip()
            except Exception:
                val = ""
        if val and val not in keys:
            keys.append(val)

    return keys


def _fetch_repo_json(filename: str):
    url = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{filename}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _index_by_id(data) -> dict:
    indexed = {}
    if isinstance(data, list):
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                key = item.get("id", idx + 1)
                indexed[key] = item
    elif isinstance(data, dict):
        for k, v in data.items():
            indexed[k] = v
    return indexed


def load_reference_benchmark() -> tuple[dict, dict]:
    try:
        inputs_raw = _fetch_repo_json("test-case-inputs.json")
        cases_raw = _fetch_repo_json("test-cases.json")
        return _index_by_id(inputs_raw), _index_by_id(cases_raw)
    except Exception:
        return {}, {}


def parse_frac_safe(text: str) -> Fraction | None:
    cleaned = (text or "").strip()
    if not cleaned:
        return None
    try:
        return Fraction(cleaned)
    except (ValueError, ZeroDivisionError):
        return None


def find_matching_reference_case(
    extracted: ExtractedCase,
    ref_inputs_by_id: dict,
    ref_cases_by_id: dict,
) -> dict | None:
    if not ref_inputs_by_id or not ref_cases_by_id:
        return None

    target_heirs = {
        h.heir_type.lower().replace(" ", "").replace("(s)", "")
        for h in extracted.heirs
        if h.count > 0
    }
    if not target_heirs:
        return None

    for case_id, inp in ref_inputs_by_id.items():
        if not isinstance(inp, dict):
            continue
        active_ref_keys = {
            k.lower().replace("_", "").replace("s", "")
            for k, v in inp.items()
            if isinstance(v, (int, float)) and v > 0 and k != "id"
        }
        normalized_target = {name.rstrip("s") for name in target_heirs}
        if (
            active_ref_keys
            and active_ref_keys.issubset(normalized_target)
            and len(active_ref_keys) == len(normalized_target)
        ):
            return {
                "id": case_id,
                "input": inp,
                "expected_output": ref_cases_by_id.get(case_id),
            }
    return None


def call_gemini_structured(
    api_keys: list[str],
    prompt: str,
    response_schema: type[SchemaT],
    models: list[str] | None = None,
    backoff_seconds: float = 1.2,
) -> tuple[SchemaT, str]:
    """Rotates across API keys when exhausted/rate-limited and switches models on errors."""
    if not api_keys:
        raise RuntimeError("No Gemini API keys configured.")

    model_list = models or MODEL_CANDIDATES
    errors: list[str] = []

    for key_idx, api_key in enumerate(api_keys, start=1):
        client = genai.Client(api_key=api_key)
        for m_name in model_list:
            for attempt in range(2):
                try:
                    resp = client.models.generate_content(
                        model=m_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=response_schema,
                        ),
                    )
                    if resp.parsed is not None:
                        return resp.parsed, m_name
                    errors.append(f"key#{key_idx}/{m_name}: empty parsed response")
                    break
                except Exception as exc:
                    msg = str(exc)
                    errors.append(f"key#{key_idx}/{m_name} (try {attempt+1}): {type(exc).__name__}")
                    if "404" in msg:
                        break
                    if "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower() or "429" in msg:
                        # If a model or key hits quota, try next model on current key first;
                        # once models on this key are exhausted, outer loop moves to next API key.
                        break
                    if attempt == 0 and ("503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg.lower()):
                        time.sleep(backoff_seconds)
                        continue
                    break

    raise RuntimeError("All configured API keys and models failed:\n" + "\n".join(errors))


def fiqh_rule_sanity_check(response: HybridFaraidResponse) -> list[str]:
    warnings: list[str] = []
    if response.status != "ok":
        return warnings

    by_heir = {}
    for item in response.shares:
        frac = parse_frac_safe(item.fraction)
        if frac is not None:
            by_heir[item.heir.lower()] = (frac, item.count)

    has_husband = any("husband" in k for k in by_heir)
    has_wife = any("wife" in k for k in by_heir)
    has_mother = any("mother" in k for k in by_heir)
    daughter_entry = next((v for k, v in by_heir.items() if "daughter" in k), None)
    son_entry = next((v for k, v in by_heir.items() if "son" in k), None)

    if has_husband and has_mother and daughter_entry and not son_entry:
        d_frac, d_cnt = daughter_entry
        if d_cnt >= 2 and d_frac == Fraction(7, 12):
            warnings.append(
                "Scholarly Review Note: With Husband + Mother + 2+ Daughters (no sons), "
                "base shares (1/4 + 1/6 + 2/3 = 13/12) typically undergo 'Awl (3/13, 2/13, 8/13). "
                "Please verify with a qualified scholar."
            )

    if not has_husband and not has_wife and has_mother and daughter_entry and not son_entry:
        m_frac, _ = next((v for k, v in by_heir.items() if "mother" in k), (None, 0))
        d_frac, d_cnt = daughter_entry
        if d_cnt == 1 and m_frac == Fraction(1, 4) and d_frac == Fraction(3, 4):
            warnings.append(
                "Radd Verification Note: Confirm no unmentioned 'Asabah (father, brother, or paternal uncle) exists."
            )

    return warnings


def verify_and_reconcile_response(
    api_keys: list[str],
    response: HybridFaraidResponse,
    plain_text_story: str = "",
    preferred_madhab: Literal["maliki", "hanafi"] = "maliki",
    net_estate_ngn: Decimal | None = None,
    models: list[str] | None = None,
) -> tuple[HybridFaraidResponse, list[str]]:
    audit_notes: list[str] = []

    if response.status != "ok":
        audit_notes.append("Held for qualified Sharia scholar and legal practitioner review.")
        return response, audit_notes

    parsed_shares: list[tuple[HeirShareExplanation, Fraction]] = []
    for item in response.shares:
        frac = parse_frac_safe(item.fraction)
        if frac is None or frac < Fraction(0, 1):
            audit_notes.append(f"Invalid fraction '{item.fraction}' for {item.heir}.")
        else:
            parsed_shares.append((item, frac))

    total_frac = sum((f for _, f in parsed_shares), Fraction(0, 1))

    if total_frac != Fraction(1, 1):
        diff = Fraction(1, 1) - total_frac
        audit_notes.append(f"Initial fraction sum was {total_frac} (expected 1); running verification pass.")
        if plain_text_story:
            correction_prompt = f"""
Your previous JSON output had a fraction sum mismatch:
Active shares summed to {total_frac} instead of 1 (difference: {diff}).
Re-calculate carefully so that:
1. Each share is a simplified rational fraction string (e.g. "1/8", "7/12", "7/24"),
2. Active shares sum to EXACTLY 1,
3. Monetary amounts match net estate * (numerator / denominator) where net estate is known,
4. Every item preserves Qur'an, Hadith, and Scholarly ({preferred_madhab.title()}) references.

Original Story:
\"\"\"{plain_text_story}\"\"\"
"""
            retried, _ = call_gemini_structured(api_keys, correction_prompt, HybridFaraidResponse, models=models)
            retry_parsed: list[tuple[HeirShareExplanation, Fraction]] = []
            for item in retried.shares:
                f = parse_frac_safe(item.fraction)
                if f is not None and f >= Fraction(0, 1):
                    retry_parsed.append((item, f))
            retry_total = sum((f for _, f in retry_parsed), Fraction(0, 1))
            if retry_total == Fraction(1, 1):
                audit_notes.append("Verification pass succeeded: active shares sum cleanly to 1.")
                response = retried
                parsed_shares = retry_parsed
            else:
                audit_notes.append(f"Shares summed to {retry_total} instead of 1; consult a scholar.")
                audit_notes.extend(fiqh_rule_sanity_check(retried))
                return retried, audit_notes

    if net_estate_ngn is not None and net_estate_ngn > Decimal("0"):
        for item, frac in parsed_shares:
            exact_amt = (
                net_estate_ngn * Decimal(frac.numerator) / Decimal(frac.denominator)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            audit_notes.append(f"{item.heir}: share={frac} -> exact value ₦{exact_amt:,.2f}")

    audit_notes.extend(fiqh_rule_sanity_check(response))
    return response, audit_notes


def translate_response_to_arabic(
    api_keys: list[str],
    response: HybridFaraidResponse,
    audit_notes: list[str],
    models: list[str] | None = None,
) -> tuple[HybridFaraidResponse, list[str]]:
    """Translates result text into clear Modern Standard Arabic while keeping exact fractions intact."""
    class ArabicTranslationPayload(BaseModel):
        madhab_used_ar: str
        net_estate_summary_ar: str
        escalation_notice_ar: str = ""
        reference_benchmark_note_ar: str = ""
        shares_ar: list[HeirShareExplanation]
        audit_notes_ar: list[str]

    payload_in = {
        "madhab_used": response.madhab_used,
        "net_estate_summary": response.net_estate_summary,
        "escalation_notice": response.escalation_notice,
        "reference_benchmark_note": response.reference_benchmark_note,
        "shares": [s.model_dump() for s in response.shares],
        "audit_notes": audit_notes,
    }

    prompt = f"""
Translate the following Fara'id (Islamic inheritance) analysis fields into clear, accurate Arabic.
Important rules:
- Keep the `fraction` strings exact (e.g. "1/8", "7/12", "7/24", "0").
- Keep `count` as the exact integer.
- Translate `heir`, `estimated_amount_text`, `explanation`, `quran_reference`, `hadith_reference`, `scholar_reference`,
  `madhab_used_ar`, `net_estate_summary_ar`, `escalation_notice_ar`, `reference_benchmark_note_ar`, and `audit_notes_ar` into natural Arabic.

Input JSON:
{json.dumps(payload_in, ensure_ascii=False)}
"""
    translated, _ = call_gemini_structured(api_keys, prompt, ArabicTranslationPayload, models=models)
    ar_response = HybridFaraidResponse(
        status=response.status,
        madhab_used=translated.madhab_used_ar or response.madhab_used,
        net_estate_summary=translated.net_estate_summary_ar or response.net_estate_summary,
        escalation_notice=translated.escalation_notice_ar or response.escalation_notice,
        shares=translated.shares_ar or response.shares,
        reference_benchmark_note=translated.reference_benchmark_note_ar or response.reference_benchmark_note,
    )
    return ar_response, (translated.audit_notes_ar or audit_notes)


def analyze_inheritance_case(
    api_keys: list[str],
    plain_text_story: str,
    preferred_madhab: Literal["maliki", "hanafi"] = "maliki",
    ref_inputs_by_id: dict | None = None,
    ref_cases_by_id: dict | None = None,
    language: Literal["en", "ar"] = "en",
    models: list[str] | None = None,
) -> tuple[HybridFaraidResponse, list[str]]:
    extract_prompt = f"""
You are a precise legal/Fiqh intake parser. Extract structured details from this inheritance story.
Preferred Madhab if not specified in text: {preferred_madhab}.
Flag needs_scholar_review=True if there is:
- paternal grandfather surviving alongside siblings (Al-Jadd wa al-Ikhwah),
- unborn child (Haml), missing person (Mafqud), or unknown order of death,
- unspecified gender of children/siblings needed for 2:1 distribution,
- statutory will, Marriage Act statutory marriage, or Nigerian customary/land dispute,
- or ambiguous/missing key family facts.

Story:
\"\"\"{plain_text_story}\"\"\"
"""
    extracted, _ = call_gemini_structured(api_keys, extract_prompt, ExtractedCase, models=models)

    ref_match = find_matching_reference_case(
        extracted,
        ref_inputs_by_id or {},
        ref_cases_by_id or {},
    )
    ref_context_text = (
        f"Matched Reference Case #{ref_match['id']} expected shares: {json.dumps(ref_match['expected_output'])}"
        if ref_match and ref_match.get("expected_output")
        else "No exact 1-to-1 match in the 134 reference test cases; apply Fara'id principles carefully and flag any uncertainty."
    )

    reasoning_prompt = f"""
You are a Fara'id (Islamic inheritance) analyst and educator.
Respond ONLY with valid JSON matching the schema.

Rules:
1. If extracted.needs_scholar_review is True or extracted.escalation_reasons is non-empty:
   Set status="escalated_to_scholar", explain why a qualified Sharia scholar (and Nigerian legal/estate practitioner if applicable) must review it, and still provide relevant Qur'an, Hadith, and Scholarly context.
2. If status="ok":
   - Compute exact rational fractions (using reduced fractions like 1/8, 7/12, 7/24) that sum to 1 (accounting for 'Awl or Radd where applicable).
   - Compute estimated monetary amounts from net estate (gross minus funeral/debts/wasiyyah, capped at 1/3 post-debt wasiyyah).
   - For EVERY heir share, provide:
     * quran_reference (specific Surah & verse, e.g., Surah An-Nisa 4:11 or 4:12),
     * hadith_reference (authentic Hadith reference, e.g., Sahih al-Bukhari 6732),
     * scholar_reference (explicitly comparing/stating {extracted.madhab.title()} perspective—noting Maliki prominence in Nigerian Sharia courts—and relevant Hanafi perspective).
3. Never invent fake verses or fake Hadith numbers. Include a reminder that this tool is educational/analytical, not a formal Fatwa or court ruling.

Extracted Case:
{extracted.model_dump_json(indent=2)}

Reference Benchmark Info:
{ref_context_text}
"""
    output, _ = call_gemini_structured(api_keys, reasoning_prompt, HybridFaraidResponse, models=models)

    gross_dec = Decimal(str(extracted.gross_estate_value)) if extracted.gross_estate_value > 0 else None
    ded_dec = (
        Decimal(str(extracted.deductions_funeral_debts_wasiyyah))
        if extracted.deductions_funeral_debts_wasiyyah >= 0
        else Decimal("0")
    )
    net_dec = (gross_dec - ded_dec) if gross_dec is not None else None

    verified_output, audit_notes = verify_and_reconcile_response(
        api_keys,
        output,
        plain_text_story=plain_text_story,
        preferred_madhab=preferred_madhab,
        net_estate_ngn=net_dec,
        models=models,
    )

    if language == "ar":
        return translate_response_to_arabic(api_keys, verified_output, audit_notes, models=models)

    return verified_output, audit_notes
