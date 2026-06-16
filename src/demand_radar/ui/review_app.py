

def _render_acquisition_page() -> None:
    import streamlit as st
    from demand_radar.ui.acquisition_service import get_acquisition_summary, get_evidence_candidates

    st.subheader("自动采集 (MVP-A)")
    summary = get_acquisition_summary()
    if not summary.get("last_run_id"):
        st.info("尚未运行采集。请运行: demand-radar run-acquisition")
        return
    st.caption(f"Last run: {summary['last_run_id']}")
    col1, col2, col3 = st.columns(3)
    col1.metric("原始信号", summary["raw_signal_count"])
    col2.metric("去重信号", summary["unique_signal_count"])
    col3.metric("重复", summary["duplicate_count"])
    col4, col5, col6 = st.columns(3)
    col4.metric("有效候选", summary["valid_candidate_count"])
    col5.metric("告警候选", summary["warning_candidate_count"])
    col6.metric("无效候选", summary["invalid_candidate_count"])
    if summary.get("by_source"):
        st.markdown("---")
        st.subheader("来源统计")
        for src, cnt in summary["by_source"].items():
            st.markdown(f"- {src}: {cnt}")
    if summary.get("errors"):
        st.markdown("---")
        with st.expander(f"错误 ({len(summary['errors'])})"):
            for e in summary["errors"][:20]:
                st.error(e)
    if summary.get("warnings"):
        with st.expander(f"警告 ({len(summary['warnings'])})"):
            for w in summary["warnings"][:20]:
                st.warning(w)
    st.markdown("---")
    candidates = get_evidence_candidates()
    valid_cands = [c for c in candidates if c.get("include_in_evidence_pack")]
    st.subheader(f"证据候选 ({len(valid_cands)}/{len(candidates)})")
    _emoji_map = {"valid": "✅", "warning": "⚠️", "invalid": "❌", "duplicate": "🔄"}
    for c in valid_cands[:30]:
        status_emoji = _emoji_map.get(c.get("validation_status", ""), "?")
        with st.expander(f"{status_emoji} [{c['source_type']}] {c.get('title') or c['candidate_id'][:50]}"):
            st.markdown(f"**URL:** {c.get('source_url') or 'N/A'}")
            st.markdown(f"**Status:** {c.get('validation_status')} | **Weight:** {c.get('source_weight', 0):.2f}")
            sigs = c.get("detected_signal_types", [])
            if sigs:
                st.markdown(f"**Signals:** {', '.join(sigs)}")
            st.text_area("原文", c.get("raw_text", "")[:400], height=80, key=f"acq_{c['candidate_id']}", disabled=True)
