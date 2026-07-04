# Phase-1c quality findings — results/run-20260628T051203Z-53aa02

Judge instrument: `claude-opus-4-8` · K=3 · margin=10pp · status=FROZEN · judge_hash=`d12c36a2c8e77a31…`
LLM-judge run: **yes**

## H5 quality floor — rubric pass-rate (skill-on must not grade worse than skill-off)

| task | model | arm | n | metric | pass-rate | mean hook | low-conf |
|---|---|---|---|---|---|---|---|
| 4 | haiku | off | 20 | exact_match | 100% | — | 0 |
| 4 | haiku | on | 20 | exact_match | 100% | — | 0 |
| 4 | opus | off | 20 | exact_match | 100% | — | 0 |
| 4 | opus | on | 20 | exact_match | 100% | — | 0 |
| 4 | sonnet | off | 20 | exact_match | 100% | — | 0 |
| 4 | sonnet | on | 20 | exact_match | 100% | — | 0 |
| 6 | haiku | off | 20 | absolute_rubric | 0% | 1.45 | 0 |
| 6 | haiku | on | 20 | absolute_rubric | 100% | 2.00 | 0 |
| 6 | opus | off | 20 | absolute_rubric | 0% | 1.30 | 0 |
| 6 | opus | on | 20 | absolute_rubric | 100% | 2.00 | 0 |
| 6 | sonnet | off | 20 | absolute_rubric | 0% | 1.95 | 0 |
| 6 | sonnet | on | 20 | absolute_rubric | 90% | 2.00 | 0 |
| 9 | haiku | off | 20 | absolute_rubric | 0% | — | 0 |
| 9 | haiku | on | 20 | absolute_rubric | 5% | — | 0 |
| 9 | opus | off | 20 | absolute_rubric | 0% | — | 0 |
| 9 | opus | on | 20 | absolute_rubric | 100% | — | 0 |
| 9 | sonnet | off | 20 | absolute_rubric | 0% | — | 0 |
| 9 | sonnet | on | 20 | absolute_rubric | 50% | — | 0 |

## H6 tier-equivalence — blind pairwise (Haiku vs Opus), rubric-passing pairs only

| task | arm | pairs | eligible | excluded | Haiku | Opus | ties | low-conf | net-pref | equivalent |
|---|---|---|---|---|---|---|---|---|---|---|
| 6 | off | 20 | 0 | 100% | 0 | 0 | 0 | 0 | — | no |
| 6 | on | 20 | 20 | 0% | 1 | 12 | 7 | 0 | 55% | no |
| 9 | off | 20 | 0 | 100% | 0 | 0 | 0 | 0 | — | no |
| 9 | on | 20 | 1 | 95% | 0 | 1 | 0 | 0 | 100% | no |

_H6 is claimed only where the gap was open skill-off and within-margin skill-on, AND the rubric floor holds (judge-spec §4). Excluded-share is the coverage caveat._
