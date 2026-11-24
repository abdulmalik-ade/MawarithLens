import os
import streamlit as st
from hybrid_faraid import (
    analyze_inheritance_case,
    load_reference_benchmark,
)

st.set_page_config(
    page_title="Fara'id AI Estate & Inheritance Assistant",
    page_icon="⚖️",
    layout="wide",
)

st.title("Fara'id (Islamic Inheritance) Analytical Assistant")
st.caption("Educational & analytical decision support with Qur'anic, Hadith, and Scholarly references.")

st.info(
    "**Important Notice:** This application provides educational and analytical *Fara'id* breakdowns "
    "with primary textual references. It is **not** a formal *Fatwa* or a court decree. Always consult "
    "a qualified Sharia scholar—and a Nigerian estate/legal practitioner where statutory marriage, wills, "
    "or land titles are involved—before distributing any estate."
)


@st.cache_data(ttl=3600)
def get_cached_benchmarks():
    return load_reference_benchmark()


ref_inputs, ref_cases = get_cached_benchmarks()

PRESETS = {
    "Custom Input": "",
    "1. Standard Family + Properties (Maliki)": (
        "A Muslim man in Lagos passed away leaving a duplex worth ₦45,000,000 and ₦5,000,000 in savings. "
        "Funeral cost ₦500,000, debts were ₦1,500,000, and he left a valid ₦2,000,000 wasiyyah. "
        "He is survived by 1 wife, 1 son, and 1 daughter."
    ),
    "2. Radd Surplus (Mother + 1 Daughter)": (
        "A Muslim man passed away leaving ₦9,000,000 net estate after debts and burial. "
        "He is survived only by his mother and 1 daughter (no spouse, no sons, no father, no siblings)."
    ),
    "3. Scholar Escalation (Grandfather + Full Brothers)": (
        "A Muslim man in Kano passed away leaving a ₦20,000,000 net estate. His father is deceased, "
        "but his paternal grandfather is still alive alongside 2 full brothers. No children or spouse."
    ),
    "4. Nigerian Statutory / Customary Conflict": (
        "A Muslim man in Lagos left a property with a dispute over a statutory marriage / formal will "
        "and customary family land claims, survived by 1 wife and 2 children."
    ),
}

with st.sidebar:
    st.header("Configuration")
    madhab_choice = st.selectbox(
        "Primary School of Jurisprudence (Madhab)",
        options=["maliki", "hanafi"],
        format_func=lambda m: "Maliki (Default in Nigerian Sharia Courts)" if m == "maliki" else "Hanafi",
    )
    preset_choice = st.selectbox("Load Sample Scenario", options=list(PRESETS.keys()))

    env_key = os.getenv("GEMINI_API_KEY", "") or st.secrets.get("GEMINI_API_KEY", "")
    user_api_key = st.text_input(
        "Gemini API Key",
        value=env_key,
        type="password",
        help="Configured automatically via Streamlit Secrets (GEMINI_API_KEY) or entered here.",
    )

story_input = st.text_area(
    "Describe the deceased, surviving relatives, properties/assets, debts, and any wasiyyah:",
    value=PRESETS[preset_choice],
    height=150,
    placeholder="Example: A Muslim man in Abuja passed away leaving a house worth ₦30,000,000...",
)

if st.button("Analyze Estate Distribution", type="primary"):
    if not user_api_key.strip():
        st.error("Please configure GEMINI_API_KEY in Streamlit Secrets or enter an API key in the sidebar.")
    elif not story_input.strip():
        st.warning("Please enter an estate and family description first.")
    else:
        with st.spinner("Analyzing heirs, verifying fractions, and gathering references..."):
            try:
                result, audit_notes = analyze_inheritance_case(
                    api_key=user_api_key.strip(),
                    plain_text_story=story_input.strip(),
                    preferred_madhab=madhab_choice,
                    ref_inputs_by_id=ref_inputs,
                    ref_cases_by_id=ref_cases,
                )

                st.subheader("Net Estate & Jurisprudence Summary")
                st.write(f"**School Applied:** {result.madhab_used.title()}")
                st.write(result.net_estate_summary)

                if result.status == "escalated_to_scholar":
                    st.warning(
                        f"**Escalated for Qualified Scholarly / Legal Review:**\n\n{result.escalation_notice}"
                    )

                if result.shares:
                    st.subheader("Heir Shares & Primary Textual References")
                    for item in result.shares:
                        with st.expander(
                            f"{item.heir} (Count: {item.count}) — Share: {item.fraction} | {item.estimated_amount_text}",
                            expanded=True,
                        ):
                            st.write(f"**Reasoning:** {item.explanation}")
                            st.markdown(f"- **Qur'an:** {item.quran_reference}")
                            st.markdown(f"- **Hadith:** {item.hadith_reference}")
                            st.markdown(f"- **Scholarly Perspective:** {item.scholar_reference}")

                if result.reference_benchmark_note:
                    st.caption(result.reference_benchmark_note)

                if audit_notes:
                    with st.expander("Verification & Audit Notes"):
                        for note in audit_notes:
                            st.write(f"- {note}")

            except Exception as exc:
                st.error(
                    "The AI service is temporarily rate-limited or unavailable. Please wait a moment and try again."
                )
