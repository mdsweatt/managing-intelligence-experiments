# Prior-Art Landscape Scan: Measuring the Token Cost of Knowledge Work at the Task Level

*Research analyst report. Current as of June 13, 2026. Findings in Thread E (vendor consoles) and Thread F (routing) go stale fast; every such claim is dated. Source tiers: Tier 1 = peer-reviewed/primary; Tier 2 = reputable independent analysis; Tier 3 = vendor docs; Tier 4 = vendor marketing/blog/forum.*

## TL;DR
- **The specific measurement you want barely exists.** No one has published reproducible, model-broken-down token *consumption* for general knowledge-work tasks ("draft an email," "summarize a doc") *with run-to-run variance*. Even OpenAI's flagship GDPval knowledge-work benchmark reports only averaged dollar *ratios* for four of its own models and explicitly omits variance — so task-level measurement on real workflows is genuinely OPEN, and is the single place your own data would add real value.
- **Almost everything around that gap is already solved.** Whether cost visibility changes behavior (cloud FinOps + 15 years of energy-feedback RCTs), the cost-driver taxonomy, "FinOps for AI" as a named discipline, and per-user/per-team token dashboards from every major vendor are all KNOWN. A "provocation tool" that merely surfaces spend is largely redundant with native consoles shipped in the last 12 months.
- **Automatic model routing is the strategic threat and it is maturing fast.** Provider-native routing (GPT-5's real-time router, default-on since Aug 7, 2025) plus Coinbase-style enterprise routing erode the value of advising humans which model to pick. The defensible wedge is *task-level unit economics tied to outcomes* — which neither consoles nor routers yet provide.

## BOTTOM LINE (one line per thread)
- **A. Measured task→token benchmarks — OPEN (with caveats).** Empirically measured token consumption exists for *coding agents* and *academic agent benchmarks*; for general knowledge work it is essentially unpublished, and almost no source reports run-to-run *variance* — the highest-value gap.
- **B. Cost decomposition & drivers — KNOWN.** The taxonomy of cost drivers is well established; bottom-up per-task→aggregate modeling is described but rarely validated against actuals publicly.
- **C. The emerging discipline — KNOWN (real but young).** "FinOps for AI" is a real, named discipline with a Linux Foundation–backed body, published framework papers, and a certification; much adjacent activity is vendor marketing.
- **D. Does cost visibility change behavior — KNOWN.** Strong, decades-deep RCT evidence (energy feedback) and FinOps showback/chargeback practice, with measured effect sizes and known decay dynamics.
- **E. Vendor-native governance — KNOWN and moving fast.** Anthropic, OpenAI, Google, Microsoft, and AWS all expose per-user or per-team usage/cost tracking and spend caps; much of a basic "make spend legible" tool is already redundant. *Dates below.*
- **F. Automatic model routing — CONTESTED maturity.** Routing exists and is default-on at OpenAI; whether it is "good and default-on" everywhere is contested, but it is maturing fast enough to be a real strategic threat.

---

## THREAD A — Measured task→token benchmarks (HIGHEST PRIORITY)

**Verdict: OPEN for general knowledge work; KNOWN for coding agents and academic agent benchmarks. Run-to-run variance is the deepest gap.**

The critical distinction the task demands — observed token *consumption* for defined tasks vs. price tables vs. capability leaderboards — separates the sources cleanly:

**What measures real token consumption (not price):**
- **OpenAI GDPval** (arXiv 2510.04374, Sept 2025; Patwardhan et al.) is the most authoritative knowledge-work benchmark: 1,320 tasks across 44 occupations (legal briefs, nursing care plans, engineering blueprints). **But, per the primary source, it does NOT report per-task token consumption for any model.** It reports model cost only as *averaged dollar ratios* for four OpenAI models (Table 2: gpt-4o, o4-mini, o3, gpt-5); Footnote 4 states "We were not able to obtain cost estimates for Claude, Gemini, and Grok"; and it reports **no variance** — Footnote 8 states they "collected three API completions per model and averaged the observed response times… [and] recorded the average invoiced cost per task." The human baseline is given in dollars (H_C = $361 average per task) but the absolute model cost is never printed — only ratios. The widely cited "~100x faster / ~100x cheaper than industry experts" line appears **only in OpenAI's blog**, not the paper, and is explicitly caveated as reflecting "pure model inference time and API billing rates." **This is the single strongest piece of evidence that task-level token measurement for general knowledge work is genuinely unpublished — even by the lab best positioned to do it.** Tier 1 (primary).
- **Artificial Analysis** reports "tokens used to run the evaluation" (input + reasoning + answer tokens) and "cost to run Intelligence Index" per model — genuine *consumption* measurement, not just price, normalized using OpenAI's tiktoken across providers. Example datapoint: "Sonnet 4.6 used 74M output tokens to run the Artificial Analysis Intelligence Index, ~3x Sonnet 4.5 (Reasoning, 25M)." **But it is measured on their academic benchmark suite** (GDPval-AA, τ²-Bench Telecom, Terminal-Bench Hard, SciCode, AA-LCR, Humanity's Last Exam, GPQA Diamond, etc.), not on repeatable business tasks. **This blurs consumption and capability: it is fundamentally a capability leaderboard that also reports consumption.** Tier 2.
- **Academic agent papers** report measured token consumption per task by model, but for narrow agent tasks: FinMaster (financial workflows; o3-mini uses up to 16,000 tokens on accounting tasks vs. ~2,000 for DeepSeek-V3, with token use rising with task complexity but not necessarily improving accuracy); UI-navigation agents (ReAct, Mobile-Agent-V2, AppAgent token breakdowns by prompt component); MCP-agent network traces. Real consumption measurements, but not generalizable to "draft an email." Tier 1.
- **Coding agents (well-covered secondary):** Anthropic's own docs state, verbatim, "Across enterprise deployments, the average cost is around $13 per developer per active day and $150-250 per developer per month, with costs remaining below $30 per active day for 90% of users." (Per Business Insider, Anthropic raised the day-rate figure from ~$6 to $13 around April 15, 2026 — itself a marker of how fast these numbers move.) This is the most concrete published per-role consumption datapoint anywhere. Tier 1 (vendor primary).

**On run-to-run variance — the deepest gap:** A 2025–2026 arXiv literature establishes that agentic LLM output (and therefore token use) is *highly non-deterministic even at temperature 0*, from floating-point non-determinism and multi-step compounding. ReasonBENCH (arXiv 2512.07795) finds "even strategies with similar average performance can display confidence intervals up to four times wider" and that top performers "incur higher and less stable costs." BuildBench shows ±6.8% strict-success swings across three identical runs of the same agent. AI21's engineering blog documents that caching breaks because "running the same agent again recomputes — but doesn't reproduce — results." A widely cited survey (Kapoor & Narayanan 2024) notes "variance across runs is rarely reported." **Implication:** the variance problem is acknowledged in research but almost never characterized for *cost* specifically — and never for general knowledge-work tasks. This is where original measurement adds the most value.

**What drives the variance** is partially characterized — output length, agentic fan-out (number of tool calls), and retrieval payload size are all named in the cost-driver literature (Thread B). The iternal.ai guide states agentic systems "require 5-30x more tokens per task than a standard chat interaction," ranging from "200-2,000 tokens" (simple chat turn) to "10,000 to over 1,000,000 tokens" (document-heavy/agentic) — but these are illustrative ranges, not measured distributions. Tier 4 (blog).

**Disconfirmation found:** The strongest reasons measured benchmarks aren't widely published: (1) token use per task is genuinely unstable (the variance literature); and (2) models and tokenizers change so fast the numbers go stale in weeks. Simon Willison documents that Anthropic's Opus 4.7 tokenizer change was "effectively a sort of invisible 40% price bump" and that "GPT 5.5 is double the price of GPT 5.4 over the API" — "the most significant price hikes" he had tracked. A benchmark measured in Q1 can be obsolete by Q2. This is a real argument that static task-level token budgeting is building on sand.

---

## THREAD B — Cost decomposition and drivers

**Verdict: KNOWN.**

A clear taxonomy of LLM cost drivers is published and consistent across sources:
- **Input context** (prompt + system prompt + conversation history, which accumulates per turn), **output length** (priced 4–8x higher than input per multiple sources), **prompt caching** (cache reads ~10% of standard input rate per Anthropic; Anthropic's Batch API gives a flat 50% discount), **agentic fan-out** (number of LLM/tool calls), and **retrieval/tool payload size**. Microsoft's M365 Copilot Agents Cost Calculator operationalizes exactly this decomposition: system-prompt tokens × every turn, average user-message tokens, average assistant-response tokens, plus per-query credit costs for graph-grounded retrieval (10 credits tenant grounding + 2 generative = 12 per query). Tier 3.
- The **Simon-Kucher / AWS / Zuora** pricing work names the same drivers from the monetization side: "Every inference, reasoning step, tool call, and retry consumes compute… cost compounds with execution depth." Tier 2/3.
- The **FinOps Foundation** publishes a paper dissecting "how token pricing really works… the hidden costs that can catch even seasoned FinOps professionals by surprise," plus papers on AI cost estimation and forecasting. Tier 2.

**Bottom-up per-task → aggregate (per user/role/team) modeling** is *described* (FinOps "cost-per-unit-of-work"; Microsoft's pilot-then-extrapolate guidance) but published validation of predicted-vs-actual is thin. The FinOps "How to Forecast AI" paper sets a success target of "AI forecasts of costs vary only within 5% of actuals per month" — a stated goal, not a demonstrated result. **This is a secondary OPEN area:** rigorous public predicted-vs-actual validation of bottom-up role/team cost models is largely absent.

---

## THREAD C — The emerging discipline ("FinOps for AI")

**Verdict: KNOWN — it is real and named, but young.**

- The **FinOps Foundation** (a Linux Foundation project since 2018) has an AI Working Group with multiple published papers: "FinOps for AI Overview," "AI Cost Estimation," "How to Forecast AI Services Costs in Cloud," "Effect of Optimization on AI Forecasting," and "Unlocking AI Business Value with FinOps." Named individuals include Rob Martin and Mike Fuller (FinOps Foundation). In 2026 the Framework was extended beyond pure cloud to AI/ML, SaaS, and licensing. There is now a **FinOps Certified: AI Value** certification. Tier 2.
- Substantive claims that hold up: AI is structurally different from cloud spend because of per-token consumption pricing (vs. per-hour-per-instance), genuine difficulty attributing multi-agent costs, and the "lack of generally accepted frameworks for cost allocation across multi-agent workloads." A practitioner blog (rikuq.com) cites a "15x cost differential between GPU and CPU compute" — treat as illustrative (Tier 4).
- **Credible voices:** FinOps Foundation staff; cloud-cost vendors with real measurement products (CloudZero, Vantage, Datadog LLM Observability, Finout); observability vendors (Langfuse, Helicone). Much of the rest is vendor content marketing.

**Separating substance from marketing:** The Foundation's neutral, framework-level material is substantive. Vendor blogs (CloudZero, Finout, nOps, emma, Holori) mostly repackage the showback/chargeback canon to sell tools.

---

## THREAD D — Does cost visibility change behavior? (THE CORE PRODUCT BET)

**Verdict: KNOWN — yes, with measured effect sizes and known decay. This is your strongest foundation, but it carries two hard caveats.**

**Residential energy feedback (gold-standard, RCT-based evidence):**
- **Allcott (2011), "Social Norms and Energy Conservation"** (J. Public Economics 95:1082–1095): using a randomized field experiment of ~80,000 Minnesota households (an early OPOWER pilot), estimated that the monthly Home Energy Report program "reduces energy consumption by 1.9 to 2.0 percent relative to baseline," with a 1.4–3.3% range across sites. Effects are strongly heterogeneous by pre-treatment usage — roughly −6.3% for the top usage decile vs. −0.3% for the bottom. Tier 1 (peer-reviewed).
- **Allcott & Rogers (2014), American Economic Review 104(10):3003–3037:** studying the program scaled to "more than six million households nationwide," documents "high-frequency 'action and backsliding'" and, critically, that "if reports are discontinued after two years, effects are relatively persistent, decaying at 10–20 percent per year. Third, consumers are slow to habituate: they continue to respond to repeated treatment even after two years." Households kept on reports saved 50–60% more in years 3–5 than those dropped. **This is the key persistence/decay finding: feedback works but requires ongoing delivery; effects decay 10–20%/yr without it.** Tier 1.
- Caveats carried by the literature itself: OPOWER utilities differ systematically from others (partner selection bias), and electronic reports have lower read rates than mailed ones — both limit generalization to a software tool.

**Cloud FinOps showback/chargeback (the directly analogous domain):**
- Consistent practitioner consensus: **showback** (visibility only) builds awareness but is "rather toothless"; **chargeback** (real budget consequences) "changes behavior, and it changes quickly." The FinOps Foundation explicitly frames internal pricing as "an economic lever" for "intentional behavior change," while also stating neither model is inherently more mature — the choice depends on accounting policy. Most practitioners report 6–18 months in showback before moving to chargeback, with ~80%+ of spend attributable before hard chargeback.
- **Critical nuance for the product bet:** the FinOps literature strongly implies *visibility alone* (showback) drives weaker, softer behavior change than *financial consequence* (chargeback). A "provocation tool" that only surfaces spend is the showback model — a real but weaker effect. Corroboration AND caution.

**LLM-specific behavior change:** Coinbase (claim 3) is a real corporate case of cost-awareness driving routing decisions. The "tokenmaxxing" leaderboards (reported by the NYT and analyzed by Willison) are a *counter*-example: visibility framed as competition *increased* consumption — Willison: "maybe don't do that if you don't want to blow your entire budget on wasteful token usage." **Effect direction depends on framing — a critical design risk.**

---

## THREAD E — Vendor-native governance (TIME-SENSITIVE; DATES BELOW)

**Verdict: KNOWN — extensive native tooling already exists. This determines what a tool would be reinventing.**

*All findings current as of June 13, 2026; this thread goes stale fast.*

- **Anthropic (Claude):** Usage & Cost Admin API since mid-2025 (token consumption by workspace, API key, model, service tier; breaks out uncached/cached/cache-creation/output tokens). In early 2026, a new **Enterprise Analytics API** added *per-named-user* cost, usage, and engagement across Claude, Claude Code, Cowork, and Office agents — true per-user cost attribution, broken down by model, context window, inference region, and speed. Org- and individual-level spend caps exist; Claude Code Console shows daily spend + per-user monthly cost (flagged as estimates). Tier 1. *Caveat: Bedrock-routed Claude Code usage does NOT appear in the Analytics API.*
- **OpenAI:** Usage dashboards and per-API-key tracking; enterprise admin consoles. Less granular per-user attribution is publicly documented than Anthropic's newest API. Tier 1.
- **Microsoft Copilot:** M365 Copilot Usage Report (adoption, active users, total/average prompts per user, agent usage, user-level table over 180 days) and Viva Insights Copilot Dashboard; Purview audit logs. **Key gap admitted by practitioners:** there is "no unified dashboard for Microsoft AI consumption" — per-seat licensing and Azure per-token consumption sit in different systems, and month-end reconciliation is manual across portals. Tier 1 (Microsoft Learn) + Tier 3 (SAMexpert).
- **AWS Bedrock:** Application Inference Profiles (tag-based cost allocation to team/app/cost-center, flowing to Cost Explorer and CUR 2.0; introduced late 2024), plus IAM-principal-based cost allocation (per-caller identity) and CloudWatch invocation logging for per-token detail. **Limitation:** AIPs deliver aggregated daily dollars, "the finest grain is per usage type per day; they do not produce per-request cost" — per-prompt token detail requires invocation logs. Tier 1 (AWS docs).
- **Google:** FinOps Foundation references Google Cloud's "Generative AI Use Case Prioritization Rubric"; Vertex/Gemini enterprise consoles exist (less surfaced in this scan). Tier 2/3.

**Third-party layer** (Langfuse, Helicone, Portkey, Datadog LLM Observability, LiteLLM, CloudZero, Finout, Vantage) already does multi-step trace-level, per-user, per-feature cost attribution — including the agentic fan-out view ("when an agent makes 6 LLM calls to answer one question, Langfuse links them into a single trace with per-step cost breakdown"). Helicone was acquired by Mintlify in early 2026 (roadmap now less clear). A Mavvrik study cited in this space found ~50% of AI product companies don't track LLM API costs at all — so demand exists, but the supply of tooling is already crowded.

**Redundancy conclusion:** The "make token spend visible per user/team" function is *already shipped* by both providers and a crowded observability market. A tool whose only value is surfacing spend is largely redundant as of mid-2026. The unmet need is *task-level* attribution ("what did 'summarize a document' cost across 50 runs?") and *outcome-linked* unit economics — which consoles do not provide (they attribute by user/key/workspace/app, not by repeatable task type).

---

## THREAD F — Automatic model routing (STRATEGIC THREAT)

**Verdict: CONTESTED maturity — routing exists and is default-on at OpenAI; "good everywhere" is not yet settled, but maturing fast.**

- **Provider-native, default-on:** OpenAI's **GPT-5 real-time router** (launched Aug 7, 2025) automatically chooses between a fast model and a "thinking" model per request; it is the *default* in ChatGPT and "continuously trained on real signals, including when users switch models, preference rates for responses, and measured correctness." **But** its launch caused a documented backlash (Fortune, Aug 12, 2025): Sam Altman admitted in a Reddit AMA (Aug 8, 2025) that "the autoswitcher was out of commission for a chunk of the day, and the result was GPT-5 seemed way dumber"; roughly 20% of Plus users reverted to GPT-4o, forcing OpenAI to restore legacy models. So routing is default-on but quality-contested. Tier 1 (OpenAI) + Tier 2 (Fortune).
- **Third-party routing:** RouteLLM (LMSYS, arXiv 2406.18665, ICLR 2025) — open-source; verbatim, its matrix-factorization router "is able to achieve 95% of GPT-4 performance using 26% GPT-4 calls, which is approximately 48% cheaper as compared to the random baseline," and with LLM-judge augmentation reaches the same quality at "14% of total calls, 75% cheaper than the random baseline" (up to 3.66x cost savings on MT-Bench). OpenRouter Auto Router (powered by Not Diamond), Martian, Unify, Portkey, IBM's router, and Morph (coding-specific: "40-70% cost savings with under 2% quality loss," ~430ms classification). IBM estimates routers "can cut inferencing costs by up to 85%." Tier 1/2.
- **Enterprise practice:** Coinbase (claim 3) routes prompts to cheaper models to hold costs flat.

**"Routing exists" vs. "routing is good and default-on":** Routing *exists* broadly and is *default-on* at OpenAI. Whether it is *reliably good* is contested (GPT-5 backlash; quality-loss debates). For your product thesis this is the central strategic risk: **if routing becomes good and default-on, advising humans which model to pick loses value.** The defensible position shifts from "which model" to "is this task worth running at all, and what does it cost per outcome." Confidence: high that this is the right risk to watch; medium on timeline.

---

## THE THREE CLAIMS TO VERIFY

**Claim 1 — Simon Willison proposed budgeting AI tokens at ~10% of an engineer's salary. → PARTIAL / largely MISATTRIBUTED in framing.**
Willison did not originate a "10% of salary" budgeting *proposal*. The actual chain: (a) Willison's Feb 7, 2026 post quotes StrongDM's internal rule — "If you haven't spent at least **$1,000 on tokens today** per human engineer, your software factory has room for improvement" — and Willison expresses *skepticism* ("If these patterns really do add $20,000/month per engineer… they're far less interesting to me"). (b) Separately, in June 2026 Willison *analyzed* Uber's $1,500/month-per-tool cap and computed that, assuming two tools, "each employee's AI spending cap is ~11% of [the ~$330,000 median Uber engineer] total compensation" — an observation, not a prescription. So a "~10–11% of salary" figure is real and tied to Willison's *analysis of Uber*, but framing it as *his proposed budget* is a misattribution. Note also the separate, larger Jensen Huang GTC 2026 pitch to give engineers "probably half of [base pay]… as tokens." Tier 1 (Willison's blog, directly fetched).

**Claim 2 — "Autonomy × attribution" pricing framework (Madhavan / Bloom / Simon-Kucher lineage). → CONFIRMED, attributed to Simon-Kucher.**
Simon-Kucher published "How to choose the right pricing model for AI agents," built on two named dimensions: **Autonomy** ("How independently does the AI operate? Does it augment a human or replace them entirely?") and **Attribution** ("How clearly can the AI's actions be linked to measurable outcomes?"), plus sophistication. The AWS/Zuora/Simon-Kucher whitepaper brands this the **COMPASS Framework**. Emergence Capital independently published a near-identical "autonomy × attribution" matrix ("Charging for Intelligence"). The "Madhavan / Bloom" attribution is **unconfirmed** in this scan — the substantive, documented sources are **Simon-Kucher** (and Emergence Capital). The framework concerns *external product pricing*, not internal cost measurement — relevant but adjacent to your use case. Tier 2.

**Claim 3 — Coinbase routes prompts to cheaper models to hold AI costs flat. → CONFIRMED (primary: Armstrong's own X post).**
Brian Armstrong (Coinbase CEO) wrote on X (~June 8, 2026), verbatim: "We're working hard on routing prompts to cheaper models where appropriate, and in some cases have been able to keep costs roughly flat, while token usage continues to grow exponentially." He predicted ~80% of workloads will move to "99% cheaper" models within 12–18 months. Widely reported (Business Insider, Benzinga, Tekedia, BeInCrypto). **Caveat:** Coinbase "has not published a technical whitepaper on its routing system," so treat the *mechanism* as asserted-not-audited — though the statement itself is primary and confirmed. Tier 2 (CEO statement via multiple outlets).

---

## SYNTHESIS — What they can stand on, what they'd be reinventing, where to measure

**What they can confidently stand on (KNOWN — don't re-prove):**
1. **Cost visibility changes behavior.** The energy-feedback RCTs (Allcott 2011; Allcott & Rogers 2014) and the FinOps showback/chargeback canon give you effect sizes from ~2% (energy, average) to "changes quickly" (chargeback) — but with two hard lessons: **(a) effects decay 10–20%/yr without ongoing delivery**, and **(b) visibility-only (showback) is weaker than consequence (chargeback).** Build for recurring nudges, not one-time reveals.
2. **The cost-driver taxonomy.** Fully mapped — adopt it, don't rebuild it.
3. **"FinOps for AI" as a discipline** with a framework and certification — align vocabulary to it for credibility with buyers.

**What they'd be reinventing (redundant as of mid-2026):**
1. **Per-user / per-team token & cost dashboards.** Shipped natively by Anthropic (incl. the per-named-user Enterprise Analytics API), Microsoft, AWS, and OpenAI, plus a crowded third-party market (Langfuse, Helicone, Datadog, CloudZero, Finout). A tool that just surfaces spend is redundant.
2. **Model price comparison / capability leaderboards.** Artificial Analysis and others own this.
3. **Telling humans which model to pick.** Increasingly automated by routers (GPT-5 router default-on; RouteLLM; OpenRouter Auto Router). An eroding value proposition.

**Where their own measurement would add genuine value (OPEN):**
1. **Task-level token consumption for general (non-coding) knowledge work, WITH run-to-run variance.** GDPval (per primary source) does not report it; Artificial Analysis measures only its academic suite; consoles attribute by user/key, not by repeatable task. *No source found that publishes "draft an email" / "summarize a document" / "research a topic with an agent" token distributions across repeated runs, broken down by model.* This is the genuine white space.
2. **Characterizing the variance and its drivers** (output length vs. agentic fan-out vs. retrieval payload) for *business* tasks — the research literature proves variance is large and under-reported but hasn't quantified it for knowledge work.
3. **Validated bottom-up role/team cost prediction** (predicted vs. actual). FinOps states a 5%-of-actuals *goal*; public validation is thin.

**Two structural risks to the whole approach (disconfirmation):**
- **Staleness:** tokenizer/price changes (Willison: Opus 4.7's "invisible 40% price bump"; GPT-5.5 "double" GPT-5.4; Anthropic raising the Claude Code day-rate from ~$6 to $13 in April 2026) can obsolete a task→token benchmark within weeks. Any measurement product must be continuously re-run, not a static report.
- **Instability:** token use per task is genuinely high-variance (ReasonBENCH, BuildBench, the agentic-reproducibility literature), so single-number "this task costs X tokens" claims are misleading without distributions — which is *also* the opportunity, if you measure and report the distribution everyone else omits.

**Net recommendation (staged):**
1. **Now — don't build the obvious thing.** A spend-visibility tool is redundant with native consoles, and a model-picker is being automated away. Kill both as standalone products.
2. **Validate the white space cheaply.** Run *your own* repeated-trial measurement of a handful of canonical knowledge-work tasks (email draft, document summary, agentic research) across the top 3–4 models, and report the *distribution* (mean, variance, tail), not a point estimate. If your measured run-to-run coefficient of variation is small enough to budget against (rule of thumb: under ~15–20%), task-level budgeting is viable; if it's larger, pivot the product to *monitoring distributions* rather than *predicting costs*.
3. **Tie it to outcomes and consequence.** Pair task-level unit economics with a chargeback-style mechanism (real budget signal), not pure showback — the behavior-change literature says visibility alone decays 10–20%/yr.
4. **Benchmarks that would change the recommendation:** if a provider or Artificial Analysis begins publishing per-task token *distributions* for general knowledge work (watch GDPval v2, which OpenAI says will add interactive/multi-draft tasks), the white space closes and you should retreat to the outcome-linkage layer. If provider-native routing becomes reliably good and default-on across vendors (watch for the GPT-5 backlash to not repeat on the next major release), abandon any "which model" advisory entirely.

*Where this scan found nothing: no public source reporting per-task token-consumption distributions for general knowledge work; no audited technical detail of Coinbase's routing system; no primary "Madhavan/Bloom" pricing-framework source; no rigorous public predicted-vs-actual validation of bottom-up team-level AI cost models.*