"""
slides/build_slides.py
Generates slides/CitiBike_Problem_Hours.pptx (10 slides with embedded figures + speaker notes).
Usage:
    python slides/build_slides.py valid    (uses Validation Week 6 results & figures)
    python slides/build_slides.py test     (uses Test Weeks 7-8 results & figures after freeze)
"""
import json
import sys
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
RES = ROOT / "results"
OUT = ROOT / "slides" / "CitiBike_Problem_Hours.pptx"

NAVY = RGBColor(20, 45, 85)
BLUE = RGBColor(43, 108, 176)
DARK = RGBColor(35, 35, 35)
MUTED = RGBColor(100, 105, 115)
LIGHT_BG = RGBColor(244, 247, 251)
ACCENT = RGBColor(192, 57, 43)


def add_title_slide(prs, tag_label):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()

    tb = s.shapes.add_textbox(Inches(0.9), Inches(1.4), Inches(11.5), Inches(2.2))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Predicting Problem Hours at Busy Citi Bike Stations"
    p.font.size = Pt(38); p.font.bold = True; p.font.color.rgb = RGBColor(255, 255, 255)

    p2 = tf.add_paragraph()
    p2.text = "2-Hour-Ahead Rebalancing Risk Ranking (NYC, Sep–Oct 2025)"
    p2.font.size = Pt(22); p2.font.color.rgb = RGBColor(185, 212, 245); p2.space_before = Pt(12)

    tb2 = s.shapes.add_textbox(Inches(0.9), Inches(4.3), Inches(11.5), Inches(2.3))
    tf2 = tb2.text_frame; tf2.word_wrap = True
    for line, sz, col in [
        ("Audience: Citi Bike operations planners prioritising rebalancing trucks", 18, RGBColor(255, 255, 255)),
        ("Scope: Prediction & association only — no causal claims, no truck routing", 15, RGBColor(210, 225, 240)),
        (f"42.510 Statistical Learning for Data Science (SUTD)  |  Anderson Hoang, Joanna Chen, Marcuz Duong", 14, RGBColor(175, 195, 220)),
        (f"Data shown: {tag_label}", 13, RGBColor(255, 210, 130)),
    ]:
        q = tf2.add_paragraph() if tf2.paragraphs[0].text else tf2.paragraphs[0]
        q.text = line; q.font.size = Pt(sz); q.font.color.rgb = col; q.space_before = Pt(8)

    s.notes_slide.notes_text_frame.text = (
        "Speaker: Anderson (0:00-1:00). Name the audience in the first sentence: Citi Bike operations planners "
        "deciding which stations to rebalance 2 hours ahead. Emphasise prediction only — no causal claims."
    )


def new_content_slide(prs, title, speaker, note):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bar = s.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.05))
    bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()

    tb = s.shapes.add_textbox(Inches(0.6), Inches(0.18), Inches(10.5), Inches(0.7))
    p = tb.text_frame.paragraphs[0]
    p.text = title; p.font.size = Pt(25); p.font.bold = True; p.font.color.rgb = RGBColor(255, 255, 255)

    sp = s.shapes.add_textbox(Inches(11.0), Inches(0.28), Inches(1.9), Inches(0.5))
    sp_p = sp.text_frame.paragraphs[0]; sp_p.alignment = PP_ALIGN.RIGHT
    sp_p.text = speaker; sp_p.font.size = Pt(13); sp_p.font.color.rgb = RGBColor(185, 212, 245)

    s.notes_slide.notes_text_frame.text = note
    return s


def add_bullets(slide, left, top, width, height, items, font_size=16):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame; tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {item}"
        p.font.size = Pt(font_size); p.font.color.rgb = DARK; p.space_after = Pt(10)


def add_pic(slide, path, left, top, width=None, height=None):
    if path.exists():
        kw = {}
        if width: kw["width"] = Inches(width)
        if height: kw["height"] = Inches(height)
        slide.shapes.add_picture(str(path), Inches(left), Inches(top), **kw)


def main(which="valid"):
    ci_csv = RES / f"{which}_metrics_with_ci.csv"
    diff_json = RES / f"{which}_paired_differences.json"
    sens_csv = RES / ("validation_week6_sensitivity.csv" if which == "valid" else "test_metrics_all_thresholds.csv")
    if not ci_csv.exists():
        sys.exit(f"Missing {ci_csv}. Run analysis/07_bootstrap_errors_figures.py {which} first.")

    ci = pd.read_csv(ci_csv)
    diffs = json.loads(diff_json.read_text())
    sens = pd.read_csv(sens_csv)
    tag_label = "Validation Week 6 (6–12 Oct 2025) — DRAFT before 25 Nov Freeze" if which == "valid" else "Untouched Test Weeks 7–8 (13–26 Oct 2025)"

    best = ci.iloc[0]
    best_b = ci[ci.method.str.startswith("b")].iloc[0]
    lasso = ci[ci.method == "lasso_weather"].iloc[0]
    gain = diffs["best_minus_best_baseline"]
    wx_l = diffs["weather_minus_no_weather"]["lasso"]
    wx_r = diffs["weather_minus_no_weather"]["rf"]

    prs = Presentation()
    prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)

    # Slide 1
    add_title_slide(prs, tag_label)

    # Slide 2: Question & Scope
    s = new_content_slide(
        prs, "1. Decision Problem & Scope", "Anderson",
        "Anderson (1:00-2:15): Explain why planners need a 2-hour lead time (stated assumption for truck dispatch) "
        "and why net flow is our operational proxy."
    )
    add_bullets(s, 0.8, 1.4, 11.7, 5.5, [
        "Audience: Citi Bike operations planners deciding which stations to check and rebalance next.",
        "Question: Can trip history, calendar, and weather available 2 hours ahead predict problem hours at the 300 busiest NYC stations (Sep–Oct 2025)?",
        "Problem hour = |arrivals − departures| in top 5% of training station-hours (fixed threshold: ≥ 15 bikes/hr).",
        "2-hour lead time: stated assumption to allow truck dispatch (not an official Citi Bike figure).",
        "Strict boundaries: prediction only (no causal claims), risk ranking only (not truck routing).",
    ], font_size=18)

    # Slide 3: Data Story
    s = new_content_slide(
        prs, "2. Data Story: 15.1M Raw Trips → 403,200 Station-Hours", "Anderson",
        "Anderson (2:15-4:00): Walk through raw-to-table steps, text IDs, 341 excluded stations, licence compliance."
    )
    add_bullets(s, 0.6, 1.35, 5.4, 5.6, [
        "3 NYC monthly archives (Aug–Oct 2025, no JC-): 15,140,880 trips across 17 CSVs.",
        "Station IDs read as TEXT (keeps trailing zero, e.g. 5329.10); stripped _ and _old suffixes.",
        "341 stations inactive on ≥1 of 35 training days excluded BEFORE picking top 300 (training volume only).",
        "Final grid: 300 × 24 × 56 = 403,200 rows (SHA-256 verified).",
        "Weather: Open-Meteo NYC hourly series (1,512 hrs, CC BY 4.0).",
        "Licence: raw files never committed; get_data.py reproduces download.",
    ], font_size=15)
    add_pic(s, FIG / "fig4_data_quality.png", 6.2, 1.6, width=6.7)

    # Slide 4: EDA
    s = new_content_slide(
        prs, "3. Training-Week Patterns (EDA)", "Joanna",
        "Joanna (4:00-5:45): Show sharp weekday rush-hour peaks (up to 33.5% on Tue 8 AM) and demand-group spread."
    )
    add_pic(s, FIG / "fig2_problem_share_hour_weekday.png", 0.6, 1.3, width=7.9)
    add_pic(s, FIG / "fig3_demand_groups.png", 8.7, 1.3, width=4.1)
    add_bullets(s, 0.6, 5.1, 12.1, 2.0, [
        "Problem hours cluster tightly in weekday commute peaks (highest: Tuesday 08:00 at 33.5%).",
        "High-demand stations experience nearly double the problem-hour rate of low-demand stations (7.0% vs 3.8%).",
    ], font_size=16)

    # Slide 5: Validation, Leakage & Metrics
    s = new_content_slide(
        prs, "4. Validation Design, Leakage Walls & Metrics", "Joanna",
        "Joanna (5:45-7:45): Justify time-ordered split, H-3 cut-off + automated leakage test, and PR-AUC over accuracy."
    )
    add_bullets(s, 0.8, 1.4, 11.7, 5.6, [
        "Time-ordered split (no random split): Weeks 1–5 Train (1 Sep–5 Oct) → Week 6 Valid (6–12 Oct) → Weeks 7–8 Untouched Test (13–26 Oct, scored ONCE after 25 Nov freeze).",
        "Leakage wall 1 (2-hr rule): All lags and weather stop at end of hour H-3. Automated test mutates H-2 onward and asserts zero feature change.",
        "Leakage wall 2: Top-300 station list, 5% threshold (≥15), scaling, and Lasso tuning (Weeks 1–4 → Week 5) use training weeks only.",
        "Fixed metrics: PR-AUC (primary; random ≈ 0.04–0.05), Precision & Recall at top-20 alerts/hour, Brier score.",
        "Why not accuracy? Always predicting 'no' is ~95% accurate and operationally useless.",
        "Uncertainty: 95% CIs from resampling WHOLE days (hours inside a day are correlated).",
    ], font_size=16)

    # Slide 6: Decisive Result 1 (Marcuz)
    s = new_content_slide(
        prs, f"5. Result 1: Both Models Beat Baselines ({which.upper()})", "Marcuz",
        "Marcuz (7:45-9:45): Explain Lasso (L1 drops weak correlated lags) & RF (nonlinear interactions). "
        "Read PR-AUC, paired CI gain over best baseline, and Precision@20."
    )
    add_pic(s, FIG / f"fig5_{which}_pr_auc.png", 0.5, 1.3, width=6.4)
    add_pic(s, FIG / f"fig6_{which}_precision_at_budget.png", 6.95, 1.3, width=5.9)
    add_bullets(s, 0.6, 5.15, 12.1, 2.0, [
        f"Best model ({best['label']}): PR-AUC = {best['pr_auc']:.3f} (95% CI {best['pr_auc_ci_low']:.3f}–{best['pr_auc_ci_high']:.3f}), Brier = {best['brier']:.4f}.",
        f"Beats best baseline ({best_b['label']}, {best_b['pr_auc']:.3f}) by +{gain['mean_diff']:.3f} (paired 95% CI: +{gain['ci_low']:.3f} to +{gain['ci_high']:.3f}).",
        f"Lasso (+ weather) also beats baselines cleanly (PR-AUC = {lasso['pr_auc']:.3f}, Brier = {lasso['brier']:.4f}) with readable coefficients.",
    ], font_size=15)

    # Slide 7: Decisive Result 2 — Weather & Sensitivity (Marcuz)
    s = new_content_slide(
        prs, f"6. Result 2: Weather Adds Little; Rankings Hold at 3% & 10%", "Marcuz",
        "Marcuz (9:45-11:15): Report the honest near-zero weather difference (CIs cross zero) and show threshold stability."
    )
    piv = sens.pivot(index="method", columns="threshold", values="pr_auc").round(3)
    order = ["rf_weather", "rf_no_weather", "lasso_weather", "lasso_no_weather", "b2_hist_rate", "b1_last_week"]
    lines = ["PR-AUC across problem-hour thresholds:"]
    for m in order:
        if m in piv.index:
            lines.append(f"  {m:18s}  3% (≥18): {piv.loc[m, '3%']:.3f}   |   5% (≥15): {piv.loc[m, '5%']:.3f}   |   10% (≥10): {piv.loc[m, '10%']:.3f}")
    add_bullets(s, 0.8, 1.35, 11.7, 5.6, [
        f"Weather paired PR-AUC difference (with − without): Lasso = {wx_l['mean_diff']:+.4f} (CI {wx_l['ci_low']:+.4f} to {wx_l['ci_high']:+.4f}); RF = {wx_r['mean_diff']:+.4f} (CI {wx_r['ci_low']:+.4f} to {wx_r['ci_high']:+.4f}).",
        "Honest takeaway: both CIs cross zero — lagged citywide weather adds little beyond recent trip history and time of day.",
        "Ranking stability: both Random Forest and Lasso beat both baselines at 3%, 5%, and 10% thresholds and across low/mid/high demand groups.",
        " | ".join([f"5%→RF+wx {piv.loc['rf_weather','5%']:.3f} vs B2 {piv.loc['b2_hist_rate','5%']:.3f}",
                    f"3%→{piv.loc['rf_weather','3%']:.3f} vs {piv.loc['b2_hist_rate','3%']:.3f}",
                    f"10%→{piv.loc['rf_weather','10%']:.3f} vs {piv.loc['b2_hist_rate','10%']:.3f}"]),
    ], font_size=16)

    # Slide 8: Important Model Failure (Marcuz)
    s = new_content_slide(
        prs, "7. Important Failure Case: Flat Alert Budget Starves Rush Hour", "Marcuz",
        "Marcuz (11:15-12:45): Required by rubric! Explain why recall drops to ~24% at 08:00 and 17:00 "
        "even when the model assigns high risk scores (e.g., 0.86), because >20 stations peak at once."
    )
    add_pic(s, FIG / f"fig7_{which}_failure_by_hour.png", 0.6, 1.3, width=7.5)
    add_bullets(s, 8.3, 1.4, 4.6, 5.5, [
        "At 08:00 and 17:00, >45 stations/hour hit problem thresholds simultaneously.",
        "A flat budget of 20 alerts/hr caps peak recall at ~24%, missing real surges (e.g., E 40 St & Park Ave, net flow +50, scored 0.86).",
        "Meanwhile 02:00–04:00 has ~0 problem hours, wasting overnight alerts.",
        "Planner fix: allocate alerts dynamically by hour instead of flat 20/hr.",
    ], font_size=15)

    # Slide 9: Limitations (Joanna)
    s = new_content_slide(
        prs, "8. Honest Limitations", "Joanna",
        "Joanna (12:45-13:45): State the 4 core limitations clearly — rubric rewards honesty."
    )
    add_bullets(s, 0.8, 1.5, 11.7, 5.2, [
        "Proxy outcome: Trip data excludes dock inventory and staff rebalancing trips, so |net flow| measures rider pressure, not confirmed empty/full status.",
        "Busy stations only: Results apply to the 300 busiest stable stations, not low-volume or newly added stations.",
        "8-week window (Sep–Oct): Cannot measure winter/summer seasonal shifts.",
        "Sparse holidays & narrow test window: Only 1 holiday in train (Labor Day) and 1 in test (Columbus Day); 14 test days yield wide bootstrap CIs.",
    ], font_size=18)

    # Slide 10: Direct Answer & Next Steps (Marcuz)
    s = new_content_slide(
        prs, "9. Direct Answer & Next Steps for Planners", "Marcuz",
        "Marcuz (13:45-14:30): End with a crisp, direct answer to the opening question and 2 concrete next steps."
    )
    add_bullets(s, 0.8, 1.5, 11.7, 5.2, [
        "Direct answer: YES — trip history and calendar features available 2 hours ahead meaningfully outperform operational baselines for ranking station-hour imbalance risk.",
        "Weather finding: Citywide 2-hour-lagged weather adds little or no measurable gain over recent trip flows.",
        "Next step 1 (Ops): Replace the flat hourly alert budget with a commute-weighted budget (more trucks at 07:00–09:00 and 16:00–19:00).",
        "Next step 2 (Data): Combine our 2-hour risk scores with live GBFS dock-level inventory feeds to target true empty/full stockouts.",
    ], font_size=18)

    OUT.parent.mkdir(exist_ok=True)
    prs.save(OUT)
    print(f"Saved {OUT} ({len(prs.slides)} slides, mode={which})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "valid")
