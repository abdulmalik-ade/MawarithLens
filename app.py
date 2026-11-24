import streamlit as st
from hybrid_faraid import (
    analyze_inheritance_case,
    collect_api_keys,
    load_reference_benchmark,
    parse_frac_safe,
)

st.set_page_config(
    page_title="MawarithLens — Fara'id Analytical Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

UI_TEXT = {
    "en": {
        "badge": "🕌 Hybrid AI + Verified Benchmark • Maliki & Hanafi Support",
        "title": "⚖️ MawarithLens — Fara'id Estate & Inheritance Assistant",
        "subtitle": "Plain-language estate intake, verified rational share checks, and three-tier Qur'an, Hadith, and Scholarly context.",
        "notice": (
            "🛡️ **Educational & Analytical Notice:** This tool supports learning and preliminary analysis only. "
            "It is **not** a formal *Fatwa* or court decree. Always consult a qualified Sharia scholar—and a "
            "Nigerian estate/legal practitioner where statutory marriage, wills, or land titles apply—before "
            "distributing any estate."
        ),
        "controls": "🎛️ Case Controls",
        "lang_label": "🌐 Language / اللغة",
        "madhab_label": "Primary School (Madhab)",
        "preset_label": "✨ Sample Scenarios",
        "benchmarks_loaded": "📚 Reference Benchmark Cases Loaded",
        "story_header": "📝 Estate & Family Story",
        "story_prompt": "Describe the deceased, surviving relatives, assets/properties, debts, and any wasiyyah:",
        "story_placeholder": "Example: A Muslim man in Abuja passed away leaving a house worth ₦30,000,000...",
        "run_btn": "🚀 Analyze Estate Distribution",
        "tip": "Tip: Pick a sample scenario on the left or write your own plain-English case.",
        "missing_key": "Service configuration is incomplete. Please contact the site administrator.",
        "empty_story": "✍️ Please enter an estate and family description before running analysis.",
        "spinner": "🔍 Parsing case, checking shares, and compiling Qur'an, Hadith & Scholarly notes...",
        "m_madhab": "🏛️ Madhab Applied",
        "m_status": "📌 Workflow Status",
        "m_heirs": "👥 Heir Lines",
        "status_ok": "Verified OK",
        "status_esc": "Scholar Review",
        "esc_title": "⚠️ Escalated for Qualified Scholarly / Legal Review",
        "esc_default": "This scenario involves a scholarly disagreement, missing facts, or statutory/customary legal overlap that requires human review.",
        "ok_title": "✅ Estate & Share Summary",
        "tab_shares": "📜 Heir Shares & Citations",
        "tab_chart": "📊 Share Weights",
        "tab_audit": "🛡️ Audit & Notes",
        "why": "💡 Explanation",
        "quran": "📖 Qur'an",
        "hadith": "📜 Hadith",
        "scholar": "🎓 Scholarly Perspective",
        "no_chart": "No numeric share percentages available to chart.",
        "no_audit": "No additional audit notes recorded.",
        "err_busy": "⏳ The AI service is temporarily busy or rate-limited. Please wait a moment and try again.",
        "dir": "ltr",
    },
    "ar": {
        "badge": "🕌 ذكاء اصطناعي هجين + حالات مرجعية • المذهب المالكي والحنفي",
        "title": "⚖️ عدسة المواريث — مساعد تحليل الفرائض والتركات",
        "subtitle": "إدخال واضح للتركة والورثة مع التحقق من الحصص الكسرية ومراجع القرآن والحديث والفقه.",
        "notice": (
            "🛡️ **تنبيه تعليمي وتحليلي:** هذه الأداة مخصصة للتعلم والتحليل الأولي فقط، وليست **فتوى رسمية** أو حكماً قضائياً. "
            "يُرجى مراجعة عالم شرعي مختص — ومستشار قانوني عند وجود زواج مدني أو وصية أو نزاع عقاري — قبل قسمة التركة."
        ),
        "controls": "🎛️ إعدادات الحالة",
        "lang_label": "🌐 Language / اللغة",
        "madhab_label": "المذهب الفقهي المعتمد",
        "preset_label": "✨ سيناريوهات جاهزة",
        "benchmarks_loaded": "📚 عدد الحالات المرجعية المحمّلة",
        "story_header": "📝 وصف التركة والورثة",
        "story_prompt": "اذكر المتوفى والورثة الأحياء والأموال والعقارات والديون وأي وصية:",
        "story_placeholder": "مثال: توفي رجل مسلم وترك منزلاً بقيمة ₦30,000,000 وزوجة وابناً وبنتاً...",
        "run_btn": "🚀 تحليل توزيع التركة",
        "tip": "نصيحة: اختر سيناريواً من القائمة الجانبية أو اكتب تفاصيل الحالة بلغتك.",
        "missing_key": "لم يتم ضبط مفاتيح الخدمة على الخادم بعد.",
        "empty_story": "✍️ يرجى إدخال وصف التركة والورثة قبل بدء التحليل.",
        "spinner": "🔍 جارٍ تحليل الحالة والتحقق من الحصص وإعداد المراجع الشرعية...",
        "m_madhab": "🏛️ المذهب المعتمد",
        "m_status": "📌 حالة التحليل",
        "m_heirs": "👥 عدد فئات الورثة",
        "status_ok": "تم التحقق",
        "status_esc": "يحتاج مراجعة علمية",
        "esc_title": "⚠️ تمت الإحالة للمراجعة الشرعية أو القانونية المختصة",
        "esc_default": "تتضمن هذه الحالة خلافاً فقهياً أو نقصاً في المعطيات أو تداخلاً نظامياً/عرفياً يتطلب مراجعة مختص.",
        "ok_title": "✅ ملخص التركة والحصص",
        "tab_shares": "📜 حصص الورثة والمراجع",
        "tab_chart": "📊 نسب الحصص",
        "tab_audit": "🛡️ ملاحظات التدقيق",
        "why": "💡 البيان والتوضيح",
        "quran": "📖 القرآن الكريم",
        "hadith": "📜 الحديث الشريف",
        "scholar": "🎓 الرأي الفقهي",
        "no_chart": "لا توجد نسب رقمية متاحة للرسم البياني.",
        "no_audit": "لا توجد ملاحظات تدقيق إضافية.",
        "err_busy": "⏳ الخدمة مشغولة مؤقتاً أو بلغت الحد المسموح. يرجى المحاولة بعد قليل.",
        "dir": "rtl",
    },
}

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

with st.sidebar:
    st.markdown("### 🌐 Display / اللغة")
    lang_choice = st.radio(
        "Choose Language",
        options=["en", "ar"],
        format_func=lambda code: "English" if code == "en" else "العربية (Arabic)",
        horizontal=True,
        label_visibility="collapsed",
    )

t = UI_TEXT[lang_choice]
is_rtl = t["dir"] == "rtl"

st.markdown(
    f"""
    <style>
        .main .block-container {{
            direction: {t["dir"]};
            text-align: {"right" if is_rtl else "left"};
        }}
        .hero-box {{
            background: linear-gradient(135deg, #0f2922 0%, #173f35 55%, #1f5446 100%);
            border: 1px solid rgba(212, 175, 55, 0.35);
            border-radius: 14px;
            padding: 1.35rem 1.6rem;
            margin-bottom: 1rem;
            color: #f8fafc;
        }}
        .hero-badge {{
            display: inline-block;
            background: rgba(212, 175, 55, 0.18);
            color: #f3d27a;
            border: 1px solid rgba(212, 175, 55, 0.45);
            border-radius: 999px;
            padding: 0.2rem 0.75rem;
            font-size: 0.78rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        .hero-title {{
            margin: 0.15rem 0 0.35rem 0;
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: #ffffff;
        }}
        .hero-sub {{
            margin: 0;
            color: #d1fae5;
            font-size: 0.95rem;
        }}
        .escalation-card {{
            background: rgba(245, 158, 11, 0.12);
            border-{"right" if is_rtl else "left"}: 5px solid #f59e0b;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin: 0.75rem 0 1rem 0;
        }}
        .verified-card {{
            background: rgba(16, 185, 129, 0.10);
            border-{"right" if is_rtl else "left"}: 5px solid #10b981;
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin: 0.75rem 0 1rem 0;
        }}
        .site-footer {{
            margin-top: 3rem;
            padding-top: 1.1rem;
            border-top: 1px solid rgba(148, 163, 184, 0.25);
            text-align: center;
            font-size: 0.88rem;
            color: #94a3b8;
        }}
        .site-footer a {{
            color: #34d399;
            text-decoration: none;
            font-weight: 500;
        }}
        .site-footer a:hover {{
            text-decoration: underline;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def get_cached_benchmarks():
    return load_reference_benchmark()


def get_configured_keys() -> list[str]:
    secrets_dict = None
    try:
        secrets_dict = dict(st.secrets)
    except Exception:
        secrets_dict = None
    return collect_api_keys(extra_secrets=secrets_dict)


ref_inputs, ref_cases = get_cached_benchmarks()
api_keys = get_configured_keys()

st.markdown(
    f"""
    <div class="hero-box">
        <div class="hero-badge">{t["badge"]}</div>
        <h1 class="hero-title">{t["title"]}</h1>
        <p class="hero-sub">{t["subtitle"]}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(t["notice"])

with st.sidebar:
    st.markdown(f"### {t['controls']}")
    madhab_choice = st.selectbox(
        t["madhab_label"],
        options=["maliki", "hanafi"],
        format_func=lambda m: "🕌 Maliki" if m == "maliki" else "📖 Hanafi",
    )
    preset_choice = st.selectbox(t["preset_label"], options=list(PRESETS.keys()))

    st.divider()
    st.caption(f"{t['benchmarks_loaded']}: **{len(ref_cases)}**")

st.markdown(f"### {t['story_header']}")
story_input = st.text_area(
    t["story_prompt"],
    value=PRESETS[preset_choice],
    height=145,
    placeholder=t["story_placeholder"],
)

col_btn, col_hint = st.columns([1.4, 3.6])
with col_btn:
    run_clicked = st.button(t["run_btn"], type="primary", use_container_width=True)
with col_hint:
    st.caption(t["tip"])

if run_clicked:
    if not api_keys:
        st.error(t["missing_key"])
    elif not story_input.strip():
        st.warning(t["empty_story"])
    else:
        with st.spinner(t["spinner"]):
            try:
                result, audit_notes = analyze_inheritance_case(
                    api_keys=api_keys,
                    plain_text_story=story_input.strip(),
                    preferred_madhab=madhab_choice,
                    ref_inputs_by_id=ref_inputs,
                    ref_cases_by_id=ref_cases,
                    language=lang_choice,
                )

                m1, m2, m3 = st.columns(3)
                m1.metric(t["m_madhab"], result.madhab_used)
                m2.metric(
                    t["m_status"],
                    t["status_esc"] if result.status == "escalated_to_scholar" else t["status_ok"],
                )
                m3.metric(t["m_heirs"], str(len(result.shares)))

                if result.status == "escalated_to_scholar":
                    st.markdown(
                        f"""
                        <div class="escalation-card">
                            <strong>{t["esc_title"]}</strong><br/><br/>
                            {result.escalation_notice or t["esc_default"]}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="verified-card">
                            <strong>{t["ok_title"]}</strong><br/>
                            {result.net_estate_summary}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if result.shares:
                    tab_cards, tab_chart, tab_audit = st.tabs(
                        [t["tab_shares"], t["tab_chart"], t["tab_audit"]]
                    )

                    with tab_cards:
                        for item in result.shares:
                            with st.expander(
                                f"{item.heir} (×{item.count})  •  {item.fraction}  •  {item.estimated_amount_text}",
                                expanded=True,
                            ):
                                st.markdown(f"**{t['why']}:** {item.explanation}")
                                st.markdown(f"- **{t['quran']}:** {item.quran_reference}")
                                st.markdown(f"- **{t['hadith']}:** {item.hadith_reference}")
                                st.markdown(f"- **{t['scholar']}:** {item.scholar_reference}")

                    with tab_chart:
                        chart_rows = {}
                        for item in result.shares:
                            frac_val = parse_frac_safe(item.fraction)
                            if frac_val is not None:
                                chart_rows[f"{item.heir} ({item.fraction})"] = float(frac_val) * 100.0
                        if chart_rows:
                            st.bar_chart(chart_rows)
                        else:
                            st.info(t["no_chart"])

                    with tab_audit:
                        if result.reference_benchmark_note:
                            st.caption(result.reference_benchmark_note)
                        if audit_notes:
                            for note in audit_notes:
                                st.markdown(f"- {note}")
                        else:
                            st.info(t["no_audit"])

            except Exception:
                st.error(t["err_busy"])

st.markdown(
    """
    <div class="site-footer" dir="ltr">
        Built by Abdulmalik Tajudeen ·
        <a href="https://abdulmalik-ade.github.io" target="_blank">Portfolio</a> ·
        <a href="https://www.linkedin.com/in/abdulmalik-tajudeen-86602b38b/" target="_blank">LinkedIn</a> ·
        <a href="https://github.com/abdulmalik-ade" target="_blank">GitHub</a> ·
        <a href="mailto:abdulmaliktajudeen5@gmail.com">abdulmaliktajudeen5@gmail.com</a>
    </div>
    """,
    unsafe_allow_html=True,
)
