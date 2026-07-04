# Phase-1d quality findings — results/run-20260702T203102Z-f704f0

Judge instrument: `gemini-3.1-pro-preview` · K=3 · margin=10pp · status=FROZEN · judge_hash=`5fd08ff3287cbd32…`
LLM-judge run: **yes**

## H5 quality floor — rubric pass-rate (skill-on must not grade worse than skill-off)

| task | model | arm | n | metric | pass-rate | mean hook | low-conf |
|---|---|---|---|---|---|---|---|
| 1 | haiku | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 1 | haiku | off | 20 | absolute_rubric | 0% | — | 0 |
| 1 | haiku | on | 20 | absolute_rubric | 45% | — | 0 |
| 1 | opus | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 1 | opus | off | 20 | absolute_rubric | 0% | — | 0 |
| 1 | opus | on | 20 | absolute_rubric | 55% | — | 0 |
| 1 | sonnet | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 1 | sonnet | off | 20 | absolute_rubric | 0% | — | 0 |
| 1 | sonnet | on | 20 | absolute_rubric | 35% | — | 0 |
| 4 | haiku | off | 20 | exact_match | 100% | — | 0 |
| 4 | haiku | on | 20 | exact_match | 100% | — | 0 |
| 4 | opus | off | 20 | exact_match | 100% | — | 0 |
| 4 | opus | on | 20 | exact_match | 95% | — | 0 |
| 4 | sonnet | off | 20 | exact_match | 100% | — | 0 |
| 4 | sonnet | on | 20 | exact_match | 100% | — | 0 |
| 6 | haiku | neutral | 20 | absolute_rubric | 0% | 1.20 | 0 |
| 6 | haiku | off | 20 | absolute_rubric | 0% | 0.95 | 0 |
| 6 | haiku | on | 20 | absolute_rubric | 95% | 1.85 | 0 |
| 6 | opus | neutral | 20 | absolute_rubric | 0% | 1.95 | 0 |
| 6 | opus | off | 20 | absolute_rubric | 0% | 1.65 | 0 |
| 6 | opus | on | 20 | absolute_rubric | 100% | 2.00 | 0 |
| 6 | sonnet | neutral | 20 | absolute_rubric | 0% | 1.95 | 0 |
| 6 | sonnet | off | 20 | absolute_rubric | 0% | 2.00 | 0 |
| 6 | sonnet | on | 20 | absolute_rubric | 100% | 1.95 | 0 |
| 7 | haiku | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 7 | haiku | off | 20 | absolute_rubric | 0% | — | 0 |
| 7 | haiku | on | 20 | absolute_rubric | 60% | — | 0 |
| 7 | opus | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 7 | opus | off | 20 | absolute_rubric | 0% | — | 0 |
| 7 | opus | on | 20 | absolute_rubric | 100% | — | 0 |
| 7 | sonnet | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 7 | sonnet | off | 20 | absolute_rubric | 0% | — | 0 |
| 7 | sonnet | on | 20 | absolute_rubric | 10% | — | 0 |
| 8 | haiku | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 8 | haiku | off | 20 | absolute_rubric | 0% | — | 0 |
| 8 | haiku | on | 20 | absolute_rubric | 15% | — | 0 |
| 8 | opus | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 8 | opus | off | 20 | absolute_rubric | 0% | — | 0 |
| 8 | opus | on | 20 | absolute_rubric | 90% | — | 0 |
| 8 | sonnet | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 8 | sonnet | off | 20 | absolute_rubric | 0% | — | 0 |
| 8 | sonnet | on | 20 | absolute_rubric | 90% | — | 0 |
| 9 | haiku | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 9 | haiku | off | 20 | absolute_rubric | 0% | — | 0 |
| 9 | haiku | on | 20 | absolute_rubric | 5% | — | 0 |
| 9 | opus | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 9 | opus | off | 20 | absolute_rubric | 0% | — | 0 |
| 9 | opus | on | 20 | absolute_rubric | 100% | — | 0 |
| 9 | sonnet | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 9 | sonnet | off | 20 | absolute_rubric | 0% | — | 0 |
| 9 | sonnet | on | 20 | absolute_rubric | 50% | — | 0 |
| 15 | haiku | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 15 | haiku | off | 20 | absolute_rubric | 0% | — | 0 |
| 15 | haiku | on | 20 | absolute_rubric | 0% | — | 0 |
| 15 | opus | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 15 | opus | off | 20 | absolute_rubric | 0% | — | 0 |
| 15 | opus | on | 20 | absolute_rubric | 95% | — | 0 |
| 15 | sonnet | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 15 | sonnet | off | 20 | absolute_rubric | 0% | — | 0 |
| 15 | sonnet | on | 20 | absolute_rubric | 50% | — | 0 |
| 23 | haiku | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 23 | haiku | off | 20 | absolute_rubric | 0% | — | 0 |
| 23 | haiku | on | 20 | absolute_rubric | 0% | — | 0 |
| 23 | opus | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 23 | opus | off | 20 | absolute_rubric | 0% | — | 0 |
| 23 | opus | on | 20 | absolute_rubric | 80% | — | 0 |
| 23 | sonnet | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 23 | sonnet | off | 20 | absolute_rubric | 0% | — | 0 |
| 23 | sonnet | on | 20 | absolute_rubric | 0% | — | 0 |
| 24 | haiku | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 24 | haiku | off | 20 | absolute_rubric | 0% | — | 0 |
| 24 | haiku | on | 20 | absolute_rubric | 0% | — | 0 |
| 24 | opus | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 24 | opus | off | 20 | absolute_rubric | 0% | — | 0 |
| 24 | opus | on | 20 | absolute_rubric | 0% | — | 0 |
| 24 | sonnet | neutral | 20 | absolute_rubric | 0% | — | 0 |
| 24 | sonnet | off | 20 | absolute_rubric | 0% | — | 0 |
| 24 | sonnet | on | 20 | absolute_rubric | 50% | — | 0 |

## H6 tier-equivalence — blind pairwise (Haiku vs Opus), rubric-passing pairs only

| task | arm | pairs | eligible | excluded | Haiku | Opus | ties | low-conf | net-pref | equivalent |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | off | 20 | 20 | 0% | 2 | 13 | 5 | 0 | 55% | no |
| 1 | neutral | 20 | 19 | 5% | 4 | 9 | 6 | 0 | 26% | no |
| 1 | on | 20 | 7 | 65% | 1 | 1 | 5 | 0 | 0% | yes |
| 6 | off | 20 | 3 | 85% | 0 | 0 | 3 | 0 | 0% | yes |
| 6 | neutral | 20 | 2 | 90% | 0 | 0 | 2 | 0 | 0% | yes |
| 6 | on | 20 | 19 | 5% | 0 | 0 | 19 | 0 | 0% | yes |
| 7 | off | 20 | 3 | 85% | 0 | 0 | 3 | 0 | 0% | yes |
| 7 | neutral | 20 | 3 | 85% | 0 | 0 | 3 | 0 | 0% | yes |
| 7 | on | 20 | 12 | 40% | 0 | 0 | 12 | 0 | 0% | yes |
| 8 | off | 20 | 19 | 5% | 0 | 2 | 17 | 0 | 11% | no |
| 8 | neutral | 20 | 19 | 5% | 0 | 0 | 19 | 0 | 0% | yes |
| 8 | on | 20 | 5 | 75% | 0 | 1 | 4 | 0 | 20% | no |
| 9 | off | 20 | 3 | 85% | 0 | 3 | 0 | 0 | 100% | no |
| 9 | neutral | 20 | 0 | 100% | 0 | 0 | 0 | 0 | — | no |
| 9 | on | 20 | 2 | 90% | 0 | 0 | 2 | 0 | 0% | yes |
| 15 | off | 20 | 6 | 70% | 0 | 6 | 0 | 0 | 100% | no |
| 15 | neutral | 20 | 0 | 100% | 0 | 0 | 0 | 0 | — | no |
| 15 | on | 20 | 0 | 100% | 0 | 0 | 0 | 0 | — | no |
| 23 | off | 20 | 10 | 50% | 0 | 5 | 5 | 0 | 50% | no |
| 23 | neutral | 20 | 0 | 100% | 0 | 0 | 0 | 0 | — | no |
| 23 | on | 20 | 0 | 100% | 0 | 0 | 0 | 0 | — | no |
| 24 | off | 20 | 19 | 5% | 0 | 1 | 18 | 0 | 5% | yes |
| 24 | neutral | 20 | 11 | 45% | 0 | 0 | 11 | 0 | 0% | yes |
| 24 | on | 20 | 1 | 95% | 0 | 1 | 0 | 0 | 100% | no |

_H6 is claimed only where the gap was open skill-off and within-margin skill-on, AND the rubric floor holds (judge-spec §4). Excluded-share is the coverage caveat._
