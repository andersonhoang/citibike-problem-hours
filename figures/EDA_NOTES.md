# EDA figures: what they show and what they mean for the models

> **DRAFT: AI-written reference text (Claude, 28 Nov 2026). Joanna to rewrite in her own words before the task
> "EDA: 4 figures from code" is marked Done** (task rule: "Two-sentence interpretation written by you, not by AI").
> Numbers come from `results/eda_summary.json`, produced by `analysis/03_eda.py` (training weeks only).

## Figure 1: net-flow distribution (`eda1_net_flow_distribution.png`)

Net flow is concentrated close to zero, and only 5.15% of training station-hours reach |net flow| ≥ 15, with long
tails in both directions (from −134 to +96 bikes per hour). Because problem hours are rare and occur in both
directions, the outcome is defined on the absolute imbalance and models are judged with PR-AUC rather than accuracy,
since a model that always predicts "no problem" would already be about 95% accurate.

## Figure 2: problem-hour share by hour of day (`eda2_problem_share_by_hour.png`)

On weekdays, problem hours spike at the commuting peaks (29.5% of station-hours at 08:00 and about 25% at 17:00),
while on weekends and the holiday the share stays below 5% all day, and overnight it is close to zero. Hour of day,
weekday versus weekend and the holiday flag are therefore likely to be strong predictors, and a flat alert budget
would spend many alerts at night when almost nothing happens.

## Figure 3: station demand groups (`eda3_demand_groups.png`)

The share of problem hours rises with station demand, from 3.8% in the lowest third of the 300 stations to 4.6% in
the middle and 7.0% in the busiest third. Busier stations carry more of the rebalancing risk, so model results should
be reported by demand group, and station-level history features are needed to capture these differences.

## Figure 4: zero-trip station-hours per day (`eda4_data_quality.png`)

Every training day has all 7,200 station-hours, and the number with zero trips stays in a steady range (about
220–780 per day, lower on most weekends), with no missing or broken days; Labor Day (487) sits between the usual
weekday and weekend levels. The table therefore looks complete enough to model, and zero-trip hours appear to be
ordinary quiet hours rather than data gaps, although Sunday 7 Sep (777, the highest day) is worth a quick check.
