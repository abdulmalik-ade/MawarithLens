import os
import streamlit as st
from hybrid_faraid import (
    analyze_inheritance_case,
    load_reference_benchmark,
    parse_frac_safe,
)

st.set_page_config(
    page_title="MawarithLens — Fara'id Analytical Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS Styling ("Spices") ---
st.markdown(
    """
    <style>
        .hero-box {
            background: linear-gradient(135deg, #0f2922 0%, #173f35 55%, #1f5446 100%);
            border: 1px solid rgba(212, 175, 55, 0.35);
            border-radius: 14px;
            padding: 1.35rem 1.6rem;
            margin-bottom: 1rem;
            color: #f8fafc;
        }
        .hero-badge {
            display: inline-block;
            background: rgba(212, 175, 55, 0.18);
            color: #f3d27a;
            border: 1px solid rgba(212, 175, 55, 0.45);
            border-radius: 999px;
            padding: 0.2rem 0.75rem;
            font-size: 0.78rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        .hero-title {
            margin: 0.15rem 0 0.35rem 0;
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: #ffffff;
        }
        .hero-sub {
            margin: 0;
            color: #d1fae5;
            font-size: 0.95rem;
        }
        .escalation-card {
            background: rgba(245, 158, 11, 0.12);
            border-left: 5px solid #f59e0b;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin: 0.75rem 0 1rem 0;
        }
        .verified-card {
            background: rgba(16, 185, 129, 0.10);
            border-left: 5px solid #10b981;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin: 0.75rem 0 1rem 0;
        }
        .ref-pill {
            font-size: 0.85rem;
            color: #e2e8f0;
            margin-bottom: 0.35rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Hero Header ---
st.markdown(
    """
    <div class="hero-box">
        <div class="hero-badge">🕌 Hybrid AI + Verified Benchmark • Maliki &amp; Hanafi Support</div>
        <h1 class="hero-title">⚖️ MawarithLens — Fara'id Estate &amp; Inheritance Assistant</h1>
        <p class="hero-sub">
            Plain-language estate intake, verified rational share checks, and three-tier
            <strong>Qur'an</strong>, <strong>Hadith</strong>, and <strong>Scholarly</strong> context.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "🛡️ **Educational & Analytical Notice:** This tool supports learning and preliminary analysis only. "
    "It is **not** a formal *Fatwa* or court decree. Always consult a qualified Sharia scholar—and a "
    "Nigerian estate/legal practitioner where statutory marriage, wills, or land titles apply—before "
    "distributing any estate."
)


@st.cache_data(ttl=3600)
def get_cached_benchmarks():
    return load_reference_benchmark()


def get_server_api_key() -> str:
    env_val = (os.getenv("GEMINI_API_KEY") or "").strip()
    if env_val:
        return env_val
    try:
        secret_val = str(st.secrets.get("GEMINI_API_KEY", "") or "").strip()
        return secret_val
    except Exception:
        return ""


ref_inputs, ref_cases = get_cached_benchmarks()
server_api_key = get_server_api_key()

PRESETS = {
    "✍️ Custom Story": "",
    "🏠 1. Standard Family + Properties (Maliki)": (
        "A Muslim man in Lagos passed away leaving a duplex worth ₦45,000,000 and ₦5,000,000 in savings. "
        "Funeral cost ₦500,000, debts were ₦1,500,000, and he left a valid ₦2,000,000 wasiyyah. "
        "He is survived by 1 wife, 1 son, and 1 daughter."
    ),
    "🌿 2. Radd Surplus (Mother + 1 Daughter)": (
        "A Muslim man passed away leaving ₦9,000,000 net estate after debts and burial. "
        "He is survived only by his mother and 1 daughter (no spouse, no sons, no father, no siblings)."
    ),
    "⚠️ 3. Scholar Escalation (Grandfather + Full Brothers)": (
        "A Muslim man in Kano passed away leaving a ₦20,000,000 net estate. His father is deceased, "
        "but his paternal grandfather is still alive alongside 2 full brothers. No children or spouse."
    ),
    "⚖️ 4. Nigerian Statutory / Customary Conflict": (
        "A Muslim man in Lagos left a property with a dispute over a statutory marriage / formal will "
        "and customary family land claims, survived by 1 wife and 2 children."
    ),
}

# --- Sidebar Controls ---
with st.sidebar:
    st.markdown("### 🎛️ Case Controls")
    madhab_choice = st.selectbox(
        "Primary School (Madhab)",
        options=["maliki", "hanafi"],
        format_func=lambda m: "🕌 Maliki (Nigeria Default)" if m == "maliki" else "📖 Hanafi",
    )
    preset_choice = st.selectbox("✨ Sample Scenarios", options=list(PRESETS.keys()))

    if server_api_key:
        active_api_key = server_api_key
        st.success("🔑 API Key configured on server")
    else:
        active_api_key = st.text_input(
            "🔑 Gemini API Key",
            value="",
            type="password",
            help="Set GEMINI_API_KEY in Render Environment Variables or Streamlit Secrets.",
        ).strip()

    st.divider()
    st.caption(f"📚 Reference Benchmark Cases Loaded: **{len(ref_cases)}**")
    st.caption("🧭 Built for clarity, verification & scholarly escalation.")

# --- Main Input Area ---
st.markdown("### 📝 Estate & Family Story")
story_input = st.text_area(
    "Describe the deceased, surviving relatives, assets/properties, debts, and any wasiyyah:",
    value=PRESETS[preset_choice],
    height=145,
    placeholder="Example: A Muslim man in Abuja passed away leaving a house worth ₦30,000,000...",
)

col_btn, col_hint = st.columns([1.4, 3.6])
with col_btn:
    run_clicked = st.button("🚀 Analyze Estate Distribution", type="primary", use_container_width=True)
with col_hint:
    st.caption("Tip: Pick a sample scenario on the left or write your own plain-English case.")

if run_clicked:
    if not active_api_key:
        st.error("🔑 `GEMINI_API_KEY` is not configured. Add it to your environment or secrets first.")
    elif not story_input.strip():
        st.warning("✍️ Please enter an estate and family description before running analysis.")
    else:
        with st.spinner("🔍 Parsing case, checking shares, and compiling Qur'an, Hadith & Scholarly notes..."):
            try:
                result, audit_notes = analyze_inheritance_case(
                    api_key=active_api_key,
                    plain_text_story=story_input.strip(),
                    preferred_madhab=madhab_choice,
                    ref_inputs_by_id=ref_inputs,
                    ref_cases_by_id=ref_cases,
                )

                # Top Summary Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("🏛️ Madhab Applied", result.madhab_used.title())
                m2.metric(
                    "📌 Workflow Status",
                    "Scholar Review" if result.status == "escalated_to_scholar" else "Verified OK",
                )
                m3.metric("👥 Heir Lines", str(len(result.shares)))

                if result.status == "escalated_to_scholar":
                    st.markdown(
                        f"""
                        <div class="escalation-card">
                            <strong>⚠️ Escalated for Qualified Scholarly / Legal Review</strong><br/><br/>
                            {result.escalation_notice or "This scenario involves a scholarly disagreement, missing facts, or statutory/customary legal overlap that requires human review."}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="verified-card">
                            <strong>✅ Estate &amp; Share Summary</strong><br/>
                            {result.net_estate_summary}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if result.net_estate_summary:
                        st.caption(result.net_estate_summary)

                # Heir Breakdown Cards + Share Chart
                if result.shares:
                    tab_cards, tab_chart, tab_audit = st.tabs(
                        ["📜 Heir Shares & Citations", "📊 Share Weights", "🛡️ Audit & Notes"]
                    )

                    with tab_cards:
                        for item in result.shares:
                            with st.expander(
                                f"👤 {item.heir} (×{item.count})  •  Share: **{item.fraction}**  •  {item.estimated_amount_text}",
                                expanded=True,
                            ):
                                st.markdown(f"**💡 Explanation:** {item.explanation}")
                                st.markdown(f"- **📖 Qur'an:** {item.quran_reference}")
                                st.markdown(f"- **📜 Hadith:** {item.hadith_reference}")
                                st.markdown(f"- **🎓 Scholarly Perspective:** {item.scholar_reference}")

                    with tab_chart:
                        chart_rows = {}
                        for item in result.shares:
                            frac_val = parse_frac_safe(item.fraction)
                            if frac_val is not None:
                                chart_rows[f"{item.heir} ({item.fraction})"] = float(frac_val) * 100.0
                        if chart_rows:
                            st.bar_chart(chart_rows, x_label="Heir & Share", y_label="Share (%)")
                        else:
                            st.info("No numeric share percentages available to chart.")

                    with tab_audit:
                        if result.reference_benchmark_note:
                            st.caption(result.reference_benchmark_note)
                        if audit_notes:
                            for note in audit_notes:
                                st.markdown(f"- {note}")
                        else:
                            st.info("No additional audit notes recorded.")

            except Exception:
                st.error(
                    "⏳ The AI service is temporarily busy or rate-limited. Please wait a moment and try again."
                )
