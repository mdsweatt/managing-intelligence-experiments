# Meridian Cargo Systems — Brand, Editorial, and Operating Reference Set

## Master Reference for Communications, Brand, and Company Policy (Internal — Revision 7)

---

## 0. About This Reference Set

This document is the consolidated reference for everyone who writes, designs, supports, or speaks on behalf of Meridian Cargo Systems. It combines two things that used to live in separate places: the brand and editorial style guide, which governs how we sound and look, and the company operating policies, which govern how we behave. They are bound together here because the same incident — a sloppy outbound email, an unauthorized data export, a missed refund — usually touches both at once, and treating voice and policy as one subject keeps the seams from showing to the customer.

Meridian Cargo Systems builds freight-visibility and shipment-orchestration software for mid-market logistics operators. Our product is named Wayfinder. Our customers are dispatchers, freight brokers, and operations managers who live inside our application for most of their working day, so the standards in this document are not cosmetic. The tone of a status message, the clarity of a refund rule, the speed of a security response — each one lands on someone trying to move a truck.

This reference set is authoritative. Where a team-specific guideline conflicts with anything written here, this document wins, and the conflict should be reported to the Brand Council so the local guideline can be corrected. Where this document is silent, use judgment consistent with its spirit, and propose an addition.

---

## 1. Brand Foundations

### 1.1 Who We Are in One Line

Meridian Cargo Systems makes freight legible. That is the sentence beneath every other sentence. When a piece of writing drifts from it — when it sells fear, or hype, or vagueness — it has drifted from the brand.

### 1.2 The Brand Personality

We describe the Meridian voice with three adjectives, in priority order: **clear, grounded, and quietly confident.** The order matters. When two of these pull against each other, clarity wins. A grounded sentence that confuses the reader has failed; a plain sentence that under-sells but informs has succeeded.

- **Clear** means the reader understands on the first pass. We would rather be plain than clever.
- **Grounded** means we speak from the operational reality our customers live in. We use the language of the dock and the dispatch desk, not the language of the boardroom deck.
- **Quietly confident** means we state what our product does without superlatives. We do not promise to "revolutionize" or "transform." We say what happens and let the reader conclude it is good.

The reason for the priority order is operational, not aesthetic. A dispatcher reading a Watchtower alert at 03:00 while a load sits stranded at a closed dock does not have spare attention for cleverness; they need the fact, fast. Every choice in this document descends from imagining that reader. When a writer is tempted toward a flourish, the test is whether the 03:00 dispatcher would thank them for it. Almost always the answer is no.

### 1.3 What We Are Not

The brand is defined as much by exclusion as by inclusion. Meridian is **not** breezy, not jokey at the customer's expense, not corporate-grandiose, and not falsely urgent. We do not manufacture scarcity ("only 3 seats left!"), we do not use countdown timers in lifecycle email, and we do not write subject lines that misrepresent the contents of a message to raise open rates. Any of these is a brand violation and should be escalated, not copied.

### 1.4 The Tagline and Approved Variants

The approved external tagline is **"Freight you can follow."** It is the only tagline that appears in paid media and on the company home page. Two internal variants are approved for specific contexts: **"See every mile"** for Live Lane feature material, and **"Catch the exception before it costs you"** for Watchtower material. No other tagline is created without Brand Council approval, and the tagline is never altered for a clever one-off — a tagline earns its value through repetition, and a version changed for a single campaign dilutes every other appearance of it.

### 1.5 The Origin Story We Tell

Meridian was founded in 2014 by two former freight brokers who were tired of calling carriers for status updates that were already stale by the time they hung up. That origin is load-bearing for the brand: we come from the operations floor, not from a software lab, and we say so. When we tell the company story we tell it from that frustration — the stale phone call — because it is true and because it is the exact pain our customers still feel. We never inflate the story into a tale of visionary disruption; it was two people solving an annoyance, and that modesty is itself on-brand.

---

## 2. Voice and Tone

### 2.1 The Difference Between Voice and Tone

Voice is constant; tone shifts with context. Our voice — clear, grounded, quietly confident — is the same whether we are announcing a feature or apologizing for an outage. Tone is how that voice adapts to the reader's state. A customer reading a release note is curious; a customer reading an incident notice is anxious; a customer reading a dunning email is embarrassed or annoyed. Tone meets them there.

### 2.2 Tone by Situation

- **Routine product UI:** Neutral and economical. Say what the control does. "Tracking paused" not "Oops! Tracking has been paused."
- **Onboarding and education:** Warm and encouraging, never condescending. Assume the reader is competent but new.
- **Errors the user caused:** Plain and non-blaming. Never "You entered an invalid date." Prefer "That date is in the past — pick a future pickup time."
- **Errors we caused:** Direct, accountable, specific. Name what broke, what we are doing, and when we will update them. Never hide behind passive voice to dodge ownership.
- **Incidents and outages:** Calm and frequent. We would rather post an update that says "still investigating" every thirty minutes than go silent for two hours.
- **Billing and dunning:** Respectful and factual. Money is sensitive; we never imply the customer is a deadbeat.

### 2.3 The Empathy-Then-Action Pattern

For any message delivering bad news, the required structure is: acknowledge the impact in one sentence, state the cause in one sentence if known, state the action and timeline, and close with where to get help. We acknowledge before we explain, and we never lead with the technical cause before naming the human impact.

### 2.4 Tone in Live Support Chat

Support chat is the one channel where the voice loosens most, because it is a conversation between two people in real time and stiffness reads as coldness. Here, contractions are encouraged, a single exclamation point is permitted when something genuinely good has happened, and matching a customer's informal vocabulary ("load" for "shipment") is acceptable. What does not loosen is accuracy and accountability: an agent never guesses at a policy, never promises a timeline they cannot keep, and never blames another team to the customer. If the answer is unknown, the correct move is "Let me check that and come right back to you," followed by actually doing so within 5 minutes.

### 2.5 Humor

Humor is allowed but rationed. It belongs in low-stakes, high-trust moments — an onboarding welcome, a 404 page, an Easter egg in the changelog — and never in incident, billing, security, or any message where the customer is anxious or out of pocket. The test for a joke is whether it would still feel kind to a customer having their worst day on the platform. If it would land as flippant to someone whose freight is stranded, it does not ship.

### 2.6 Localization Note

Although the product is single-sourced in American English today, all customer-facing copy is written to translate cleanly: short sentences, no untranslatable idioms, no humor that depends on a pun, and no embedded text in images. This discipline costs us nothing now and saves a full rewrite when we localize, which the product roadmap anticipates within 18 months.

---

## 3. Grammar, Mechanics, and Formatting

### 3.1 The House Standard

Our editorial baseline is the Chicago Manual of Style, **with the documented exceptions below.** Where Chicago and these exceptions disagree, the exceptions win for Meridian content.

### 3.2 Documented Exceptions

- **Serial comma:** Always use it. "Trucks, trailers, and chassis," never "trucks, trailers and chassis."
- **Em dashes:** Use spaced en dashes ( – ) in body copy, not closed em dashes, for visual breathing room on screen. This is a deliberate departure from Chicago.
- **Numerals:** Spell out zero through nine in prose; use numerals for 10 and above. **Exception:** always use numerals for anything measurable — money, time, distances, weights, percentages, version numbers, and quantities of shipments — regardless of size. Write "3 shipments" and "5 minutes," but "three reasons to upgrade."
- **Oxford spelling:** We use American spelling throughout ("color," "organize"), with no regional variants, because our documentation is single-sourced.
- **Sentence-case headings:** All headings and buttons are sentence case, not title case. "Create shipment," never "Create Shipment." (This document's section titles are an internal-reference exception; customer-facing headings follow the rule.)

### 3.3 Punctuation Specifics

- One space after a period, never two.
- Use straight quotes in code and curly quotes in prose.
- Avoid exclamation points in product UI entirely; allow at most one per marketing email.
- Never use ALL CAPS for emphasis; use bold sparingly instead.

### 3.4 Dates, Times, and Numbers

- Dates in customer-facing copy use the format "14 March 2026" (day, month spelled out, year). Never use all-numeric dates like 03/14/26, which read differently across regions.
- Times always include the time zone abbreviation and are written in 24-hour format in operational contexts ("Pickup window opens 08:00 CT") and 12-hour format in marketing ("Join us at 9 a.m. CT").
- Currency is always written with the ISO code and symbol on first use ("USD $1,200") and the symbol alone thereafter.

### 3.5 Lists and Parallelism

Every item in a list begins with the same part of speech — all verbs, or all nouns, never a mix. A list with fewer than 3 items is usually better as a sentence; a list with more than 7 items usually wants subheadings. Ordered lists are reserved for genuine sequences (steps that must happen in order); everything else uses bullets. We never punctuate list items with a trailing semicolon-and-"and"; each bullet stands alone.

### 3.6 Links and Cross-References

Link text describes the destination — "see the refund policy," never "click here." Links are never the only way information is conveyed; the sentence still makes sense if the link is stripped out, because email clients and screen readers do not all render links the same way. Internal cross-references in customer documentation name the destination article rather than relying on a fragile section number that renumbers when content is added.

### 3.7 Abbreviations and Acronyms

An acronym is spelled out on first use with the acronym in parentheses, then used freely. We do not assume the reader knows freight-industry shorthand: "bill of lading (BOL)" on first use, not bare "BOL." The exception is universally understood terms (API, URL, PDF), which need no expansion. We never invent new acronyms for Meridian features — a feature has a name, not a code.

---

## 4. Terminology — The Do and Don't List

### 4.1 Product and Feature Names

- The company is **Meridian Cargo Systems** on first reference and **Meridian** thereafter. Never "MCS" in customer-facing copy.
- The product is **Wayfinder**, always capitalized, never "the Wayfinder" and never "wayfinder."
- The mobile companion app is **Wayfinder Go**. The carrier-facing portal is **Meridian Carrier Hub**, "Carrier Hub" on later reference.
- The real-time tracking feature is **Live Lane**, two words, both capitalized.
- The automated exception-alerting feature is **Watchtower**. Do not write "the watchtower feature"; write "Watchtower."
- The analytics and reporting module is **Meridian Insight**, "Insight" on later reference. The billing and subscription area is **Account**, lowercase except when naming the screen ("the Account screen").
- The public developer interface is the **Wayfinder API**, never "the Meridian API." API endpoints and parameters are always set in monospace in documentation.

### 4.2 Capitalization Quick Table

To settle the most frequent disputes: capitalize Meridian, Wayfinder, Wayfinder Go, Carrier Hub, Live Lane, Watchtower, and Meridian Insight. Do not capitalize generic nouns even when they feel important — "shipment," "carrier," "exception," "tracking," "dashboard," and "alert" are common nouns and stay lowercase unless they begin a sentence. A feature name is capitalized; the activity the feature performs is not. "Watchtower flagged an exception" is correct; "the Watchtower flagged a Watchtower exception" is not.

### 4.3 Words We Use

- "Shipment," not "load" or "freight piece," in customer-facing copy (though "load" is fine in informal support chat with a broker who uses it).
- "Carrier," not "trucker" or "hauler."
- "Delay," not "late" — "late" assigns blame; "delay" describes a state.
- "Customer," not "user," in all external writing. "User" is acceptable internally and in technical docs.

### 4.4 Words We Avoid

- Never "revolutionary," "game-changing," "seamless," "frictionless," "best-in-class," or "world-class." These are empty and violate "quietly confident."
- Never "guys" to address a mixed or unknown group; use "everyone," "folks," or "team."
- Avoid "simply," "just," and "easy" when instructing — they shame a reader who finds the step hard. Write "Select Export," not "Simply just select Export."
- Never "crazy," "insane," or "dumb" to describe situations or volumes.

### 4.5 Inclusive Language

Use gender-neutral language by default. Use "they" as a singular pronoun when gender is unknown. Avoid idioms that assume physical ability or cultural background. When describing customers, never reference protected characteristics unless directly relevant to the content. Job titles are neutral — "operations manager," not "operations man" — and example names in documentation rotate across a deliberately diverse set so the product imagery does not implicitly picture one kind of customer.

---

## 5. Visual and Format Identity

### 5.1 Logo Usage

The Meridian wordmark must always appear with a minimum clear space equal to the height of the "M" on all sides. Never stretch, recolor, rotate, or add effects to the wordmark. The minimum legible size is 24 pixels tall on screen and 12 millimeters in print. Never place the wordmark on a background with less than a 4.5:1 contrast ratio.

### 5.2 Color

- **Primary:** Meridian Slate (#1F2A37) for text and primary surfaces.
- **Accent:** Signal Amber (#F2A900), used only for calls to action and active states, never for body text.
- **Status colors are fixed and may not be repurposed:** green (#2E7D32) for on-time, amber (#F2A900) for at-risk, red (#C62828) for delayed or failed. Because roughly 1 in 12 men have some color-vision deficiency, status is **never** communicated by color alone — always pair it with an icon or label.

### 5.3 Typography

The brand typeface is Inter for screen and Source Serif for long-form print. Body text is never set below 14 pixels on screen. Line length in long-form content targets 60 to 75 characters. Never justify body text; always set it flush left, ragged right.

### 5.4 Accessibility Floor

All customer-facing surfaces must meet WCAG 2.1 AA as a minimum. Every image carries descriptive alt text; every interactive control is reachable by keyboard; no information is conveyed by color alone (see 5.2). This is a floor, not a target — exceeding it is encouraged, falling below it is a defect.

---

## 6. Acceptable Use Policy

### 6.1 Scope

This policy governs how Meridian employees, contractors, and authorized partners may use company systems, the Wayfinder platform, and any data accessed through them. It applies to all devices that touch company resources, whether company-owned or personal.

### 6.2 Permitted and Prohibited Use

Company systems are provided for legitimate business purposes. Incidental personal use is permitted provided it is lawful, does not consume significant resources, and does not interfere with duties. The following are strictly prohibited: accessing customer data without a documented business need; sharing credentials with any other person; installing unapproved software on systems that process customer data; attempting to bypass security controls; and using company systems to harass, defame, or discriminate.

### 6.3 Credential and Access Rules

Each person is assigned individual credentials and is accountable for all activity under them. Shared or generic accounts are prohibited for any system that touches customer data. Access is granted on a least-privilege basis: a person receives only the access their role requires, and access is reviewed quarterly. When an employee changes roles, their old access is revoked within 5 business days of the change.

### 6.4 Acceptable Use Enforcement

Violations are handled progressively for minor first offenses — a documented conversation, then a written warning — but serious violations, including any deliberate access to customer data without authorization, may result in immediate termination and, where applicable, referral to law enforcement.

### 6.5 Use of AI Tools

Employees may use approved AI assistants for drafting, summarizing, and coding, but never paste Confidential or Restricted data (Section 7.1) into any tool that has not been reviewed and approved for that tier. Customer shipment data, contracts, credentials, and personal data are never pasted into a general-purpose assistant. AI-generated customer-facing copy is treated as a draft, not a publish: a human reviews it for accuracy and brand fit before it ships, and the human is accountable for what goes out.

### 6.6 Email and Calendar Hygiene

Company email is for company business; auto-forwarding company email to a personal account is prohibited because it moves data outside our controls. External recipients on an email containing Confidential data are confirmed deliberately, not by autocomplete — a mis-tabbed address is the most common accidental disclosure we see. Calendar invitations for sensitive meetings carry no Confidential detail in the title or body, since invitations propagate to attendees' personal devices.

### 6.7 Physical and Remote Workspace

Screens displaying customer data are not visible to others in public spaces; a privacy screen is required for any work with Confidential data outside a controlled office. Company devices are never left unlocked and unattended. Printed material containing Confidential data is shredded, never recycled intact, and visitors to any office are escorted in areas where customer data may be on screen.

---

## 7. Data Handling and Privacy Policy

### 7.1 Data Classification

All data is classified into four tiers, and the handling rules below are tied to the tier:

- **Public:** Marketing material, published documentation. No restrictions.
- **Internal:** Org charts, internal process docs. Not for external sharing.
- **Confidential:** Customer shipment data, contracts, pricing. Encrypted in transit and at rest; access logged.
- **Restricted:** Authentication secrets, encryption keys, and any payment-card or government-ID data. Access limited to named individuals; every access generates an audit event.

### 7.2 Customer Data Ownership and Use

Customer shipment data belongs to the customer, not to Meridian. We process it solely to provide the service. We do **not** sell customer data, and we do **not** use identifiable customer shipment data to train models or for any purpose beyond delivering and improving the service the customer is paying for. Aggregated and fully de-identified statistics may be used for benchmarking and product analytics.

### 7.3 Data Retention

- **Active shipment records** are retained for the life of the account plus 7 years, to meet freight-industry recordkeeping obligations.
- **Support transcripts** are retained for 24 months, then deleted.
- **Application and access logs** are retained for 13 months.
- **Marketing contact data** is deleted within 30 days of an unsubscribe request unless an active contract requires otherwise.
- A customer may request export of their data at any time in a machine-readable format, delivered within 30 days of a verified request.

### 7.4 Data Subject and Deletion Requests

A verified request to delete personal data is honored within 30 days, except where retention is legally required (see 7.3 freight recordkeeping), in which case we explain the obligation and the date the data will become eligible for deletion. Requests are verified against the account of record before any action is taken; we never act on an unverified deletion request, because an unverified request is a plausible account-takeover vector.

### 7.5 Cross-Border Transfer

Customer data is stored in the customer's home region by default — North American customers in our US-East region, European customers in our EU-Central region. Data does not leave its home region except through a documented and contractually permitted transfer mechanism. A customer's region is set at provisioning and is never changed silently.

### 7.6 Breach Notification

If a confirmed breach affects customer personal data, Meridian notifies affected customers without undue delay and in no case later than 72 hours after the breach is confirmed. The notification states what data was affected, what we have done, and what the customer should do. We notify even when we are not legally required to, because silence costs more trust than disclosure.

### 7.7 Sub-Processors

Meridian uses a limited set of vetted sub-processors — cloud hosting, email delivery, payment processing, and error monitoring — each under a data-processing agreement that binds it to standards no weaker than our own. The current list of sub-processors is published on our trust page and customers are notified at least 30 days before a new sub-processor that handles customer personal data is added, so a customer with an objection has time to raise it. We never route customer data through an unlisted processor.

### 7.8 Consent and Marketing Contact

Marketing email goes only to people who have opted in or who fall under a legitimate-interest basis for an existing business relationship, and every such message carries a working unsubscribe. We honor an unsubscribe across all marketing streams, not just the one the customer clicked from — a single unsubscribe is a global one. Transactional and security messages (receipts, incident notices, breach notifications) are not marketing and continue regardless of marketing preferences, because a customer cannot opt out of being told their account was breached.

### 7.9 De-Identification Standard

When we say data is "de-identified" we mean direct identifiers are removed and the result is aggregated such that no individual customer or shipment can be re-identified from it, even by combining it with other data we hold. A dataset that could be re-identified by joining it to another table is not de-identified and is treated as Confidential. This standard exists so that the benchmarking permitted in 7.2 cannot quietly become a privacy hole.

---

## 8. Refund and Service-Level Policy

### 8.1 Subscription Refunds

Wayfinder is sold as an annual or monthly subscription. **Customers may request a full refund within 30 days of the initial purchase or renewal, no questions asked. The one exception is usage-based overage charges, which are non-refundable once the underlying shipments have been processed, because the service has already been delivered.** After the 30-day window, subscriptions are non-refundable but may be canceled to stop future billing.

### 8.2 Cancellation

A customer may cancel at any time. Monthly plans stop at the end of the current billing period; annual plans stop at the end of the paid term, with no partial-year refund except within the 30-day window in 8.1. We never impose cancellation fees and we never make cancellation harder than signup — the cancel control is reachable in no more than 3 clicks from the account screen.

### 8.3 Service-Level Agreement

For customers on the Business and Enterprise tiers, Wayfinder commits to **99.9% monthly uptime**, measured as the percentage of minutes in the calendar month the core tracking API is available. Scheduled maintenance, announced at least 5 business days in advance and held within the posted maintenance window (Sundays 02:00–05:00 CT), does not count against uptime.

### 8.4 SLA Credits

When monthly uptime falls below the commitment, affected Business and Enterprise customers receive service credits on the following schedule, applied to the next invoice:

- **99.0% to 99.9%:** 10% credit
- **95.0% to 98.99%:** 25% credit
- **Below 95.0%:** 50% credit

Credits are the sole remedy for an SLA miss and are capped at 50% of one month's fee. The customer must request the credit within 30 days of the affected month, and we apply it within one billing cycle of a valid request.

### 8.5 Support Response Targets

Support response targets vary by severity and tier. For Enterprise customers: Severity 1 (service down) is acknowledged within 30 minutes, 24/7; Severity 2 (major impairment) within 2 hours during business hours; Severity 3 (minor) within 1 business day. For Business customers, targets are 1 hour, 4 hours, and 2 business days respectively. These are response targets, not resolution guarantees, and they are distinct from the uptime SLA in 8.3.

### 8.6 Billing Mechanics

Invoices are issued on the first day of the billing period and are due within 30 days (net 30). A failed payment triggers a polite dunning sequence: a reminder at day 1, day 7, and day 14 after the failure, with service continuing throughout. Service is suspended only after day 30 of non-payment, and never without a final notice sent at least 5 business days before suspension. We never suspend an Enterprise account for non-payment without a human at Meridian speaking to a human at the customer first, because an enterprise outage caused by a billing glitch is its own incident.

### 8.7 Price Changes

A price increase is communicated to existing customers at least 60 days before it takes effect, and never applies mid-term — an annual customer keeps their price until renewal. We do not raise the price of a plan a customer is mid-contract on, and we do not use a confusing tier change to engineer an effective increase. Promotional pricing states its end date plainly at sign-up; we never let a promotional rate lapse silently into a higher one without a clear reminder 30 days ahead.

### 8.8 Disputes and Chargebacks

A customer who disputes a charge is heard before any collection step. If the dispute has merit, we refund or credit promptly; if it does not, we explain the charge with reference to the specific rule in this policy, in plain language. We treat a chargeback as a signal that our billing was unclear, not as an act of bad faith, and we review the messaging that led to it.

### 8.9 Definition of Downtime

For the SLA in 8.3, "downtime" means the core tracking API returns errors or fails to respond for more than 1 minute in a rolling 5-minute window, measured from our external monitoring. Degraded performance that still returns correct data within 5 seconds is not downtime. A single customer's connectivity problem is not downtime. This definition is published so the SLA is measurable the same way by both sides, rather than argued case by case.

---

## 9. Communications and PR Policy

### 9.1 Who Speaks for Meridian

Only designated spokespeople speak to the press on the record. Any media inquiry — including a casual one from a reporter on social media — is routed to Communications within the same business day and is not answered directly, even to say "no comment," without coordination. This is not about secrecy; it is about one company speaking with one voice.

### 9.2 Social Media

Employees may identify as Meridian staff on personal accounts but must include a clear disclaimer that views are their own, and must never disclose confidential or restricted information (see Section 7). Personal posts about customers, even positive ones, require the customer's written consent because a shipment relationship is itself confidential.

### 9.3 Incident Communications

During a service incident, the status page is the single source of truth, updated at least every 30 minutes for any Severity 1 incident until resolution. We post the first acknowledgment within 15 minutes of confirming a Severity 1 incident. We follow the empathy-then-action pattern (Section 2.3): impact first, cause if known, action and timeline, where to get help. We publish a public post-incident review within 5 business days of any Severity 1 incident, written in plain language and naming what failed without blaming individuals.

### 9.4 Embargoes and Pre-Announcements

We honor every embargo we agree to, to the minute. We do not pre-announce features that lack a committed ship date, because a missed pre-announcement spends trust we cannot easily refill. Forward-looking statements in any external communication are clearly labeled as such and never presented as committed availability.

### 9.5 Comparative and Competitive Claims

Any claim that compares Wayfinder to a named competitor must be factually substantiated, current within 90 days, and reviewed by Legal before publication. We criticize categories of approach, never individual competitors by name in disparaging terms, consistent with "quietly confident."

### 9.6 Customer References and Case Studies

We never name a customer publicly without their written permission, and a permission is scoped — a customer who agreed to a logo on our wall has not thereby agreed to a press quote. Case studies are reviewed by the named customer before publication, and any figures in them are ones the customer has approved us to use. When permission is withdrawn, we remove the reference promptly rather than arguing the original grant.

### 9.7 Crisis and Sensitive Topics

For any event touching safety, legal exposure, layoffs, or a security breach, all external communication routes through a designated crisis lead and is reviewed by Legal before it goes out. The first principle of crisis communication is the same as the everyday principle, only sharper: tell the truth, tell it early, and tell it from the impact outward. We never speculate publicly about a cause we have not confirmed, and we never minimize an impact to protect short-term perception, because the correction costs more than the candor would have.

### 9.8 Internal Communication During Incidents

Externally we speak with one voice; internally, during an incident, we over-communicate. A single incident channel carries the running state, a named incident commander owns decisions, and timestamps are in a single zone (CT) to avoid confusion across a distributed team. Internal candor about what went wrong is protected — the post-incident review is blameless by policy, on the understanding that people who fear blame hide the information that prevents the next outage.

---

## 10. Security Basics

### 10.1 Passwords and Authentication

- Passwords for company systems are a minimum of 14 characters and are checked against a known-breached-password list at creation.
- Passwords rotate every 90 days for any account with access to Confidential or Restricted data; accounts touching only Public or Internal data are exempt from forced rotation in favor of length and breach-checking.
- Multi-factor authentication is mandatory for all employees and is required for all customer accounts on the Enterprise tier. Hardware security keys are required for anyone with Restricted-tier access.
- After 5 consecutive failed login attempts, an account is locked for 15 minutes.

### 10.2 Device Security

Company-managed devices encrypt their disks at rest, lock automatically after 10 minutes of inactivity, and run endpoint protection that may not be disabled. Personal devices used for work ("bring your own device") must meet the same encryption and lock standards and are enrolled in a management profile limited to company data — Meridian never accesses personal content on a personal device.

### 10.3 Phishing and Social Engineering

The single most common attack we face is a phishing email impersonating an executive or vendor and requesting an urgent payment or credential. The rule is simple and absolute: **no payment, credential, or data-access change is ever executed on the basis of an email or chat message alone.** Any such request is verified through a second, independent channel (a known phone number, never one supplied in the suspicious message) before action. Reporting a suspected phishing message is always correct and is never penalized, even if it turns out to be legitimate.

### 10.4 Patching and Vulnerability Management

Critical security patches are applied to production systems within 7 days of release; high-severity patches within 30 days. A vulnerability disclosed by an external researcher is acknowledged within 2 business days, and we operate a published responsible-disclosure policy with a commitment never to pursue legal action against good-faith researchers who follow it.

### 10.5 Secrets and Keys

Credentials, API keys, and encryption keys are never committed to source control, never sent over email or chat, and never logged. They are stored only in the approved secrets manager. A secret that is exposed — even briefly, even in a private repository — is treated as compromised and rotated immediately, on the principle that we cannot prove it was not copied.

### 10.6 Backups and Recovery

Customer data is backed up continuously with point-in-time recovery, and backups are encrypted with keys separate from the production keys. We test recovery from backup at least quarterly, because an untested backup is a hope, not a plan. Our recovery-point objective is 5 minutes of data and our recovery-time objective is 4 hours for the core service; these targets are published and are part of how we are held to account internally.

### 10.7 Access Reviews and Offboarding

All access to systems handling Confidential or Restricted data is reviewed quarterly by the data owner, and any access no longer justified by a role is revoked at the review. When a person leaves the company, all access is revoked within 4 hours of their departure being confirmed, and for a departure under sensitive circumstances, access is revoked before the person is notified. Offboarding includes collecting devices, disabling credentials, and rotating any shared secret the person could have known.

### 10.8 Vendor and Supply-Chain Security

Before a new vendor touches customer data or company systems, it passes a security review proportional to its access. Software dependencies are scanned for known vulnerabilities on every build, and a dependency with a critical known vulnerability blocks the release until it is patched or mitigated. We pin our dependencies and review changes to them, because a quietly swapped dependency is a classic supply-chain attack.

### 10.9 Logging and Monitoring

Security-relevant events — logins, access to Restricted data, configuration changes, and privilege escalations — are logged to a tamper-evident store and monitored for anomalies. Logs never contain secrets or full payment-card numbers (see 10.5 and 7.1). An alert on anomalous access pages the on-call security responder, who acknowledges within 15 minutes around the clock for any alert touching Restricted data.

---

## 11. Writing for Specific Channels

### 11.1 Product UI Microcopy

Microcopy is the highest-leverage writing we do because every customer reads it. Buttons are verbs in sentence case ("Create shipment," "Resend invite"). Empty states explain what the customer will see once they act and offer the first step. Error messages name the problem, the cause if known, and the fix, in that order, and never expose a stack trace or internal error code to the customer.

### 11.2 Email

Subject lines are honest and specific — they describe the contents accurately and are never bait. Transactional email (receipts, alerts) is plain and immediate. Lifecycle email (onboarding, re-engagement) carries at most one call to action and one accent-colored button. Every marketing email includes a working one-click unsubscribe, and unsubscribe requests are honored within 30 days, per Section 7.3, though our practical target is immediate.

### 11.3 Documentation

Documentation is task-oriented, organized around what the customer is trying to do, not around how the product is built internally. Every procedure is numbered, every screenshot carries alt text, and every article shows a last-reviewed date. An article older than 12 months without review is flagged stale and is not trusted until re-reviewed.

### 11.4 In-Application Notifications

Notifications respect the customer's attention. A notification fires only when it is actionable or materially informative; we never notify for the sake of engagement. Watchtower exception alerts (Section 4.1) are the canonical example — they fire when a shipment is at risk, with the specific exception named, never as a generic "something happened."

---

## 12. Governance and Change Control

### 12.1 The Brand Council

This reference set is owned by the Brand Council, a standing group with representation from Communications, Design, Support, Legal, and Security. The Council meets monthly, reviews proposed changes, and is the escalation point for any conflict between this document and a local guideline.

### 12.2 How This Document Changes

Any change to this reference set is proposed in writing, reviewed by the Brand Council, version-stamped, and dated before it takes effect. The revision number on the title line increments with every approved change. Nobody edits this document unilaterally; the whole point of a shared reference is that it is shared, and a silent edit is indistinguishable from a brand drift.

### 12.3 Exceptions

A team that needs an exception to any rule here requests it from the Brand Council with a stated reason and a sunset date. Exceptions are time-boxed and never permanent; an exception that wants to be permanent is really a proposed change to the rule, and should be filed as one.

### 12.4 Training and Onboarding

Every new employee in a customer-facing, design, writing, or engineering role reads this document in their first week and confirms it. The Council publishes a short summary of every change so that people who read the full document once are kept current without re-reading it in full.

---

## 13. Worked Examples

### 13.1 An Outage Notice, Done Right

> **Live Lane tracking is delayed for some shipments.** Since 14:10 CT, tracking updates for a subset of shipments have been arriving late. Your shipments are still moving; only the in-app updates are affected. We have identified the cause — a backlog in our carrier-feed processor — and are clearing it now. We will post the next update by 15:00 CT. For an urgent shipment, contact Support and we will check its status manually.

This works because it leads with impact, reassures on the real-world concern (the freight is still moving), names the cause plainly, commits to a next update time, and offers a path to help — the empathy-then-action pattern in four sentences.

### 13.2 A Refund Reply, Done Right

> Thanks for reaching out. You purchased your annual plan 12 days ago, which is inside our 30-day refund window, so I have processed a full refund of USD $1,200 to your original payment method; it should appear within 5 to 10 business days. One note: the overage charges from last week are not included, because those shipments were already processed and overage is non-refundable once the service is delivered. You can keep using Wayfinder until the end of your current period.

This works because it confirms eligibility against the actual rule, states the amount and timeline concretely, names the single exception honestly without hiding it, and stays respectful throughout.

### 13.3 An Error Message, Done Right

Instead of "Error 422: invalid payload," write: "We couldn't create that shipment — the pickup date is in the past. Choose a future pickup time and try again." It names the problem in the customer's terms, gives the cause, and tells them exactly what to do, with no internal code leaking through.

### 13.4 A Phishing Test, Resolved Right

> An agent receives a chat from someone claiming to be the CFO, urgently asking them to change the bank details on a vendor payment before a deadline. The agent does not act. They reply that they will confirm, then phone the CFO on the number in the company directory — not any number in the message. The request turns out to be fake, and the agent is thanked, not penalized, for the delay.

This works because it applies the Section 10.3 rule without exception: no payment or access change on a message alone, verified on a known second channel. The urgency in the message is itself the tell — manufactured urgency is the attacker's main tool.

### 13.5 A Data-Deletion Request, Handled Right

> A customer emails asking us to delete all their data immediately. We thank them, verify the request against the account of record, and explain plainly: their marketing contact data will be removed within 30 days, but their shipment records must be retained for 7 years to meet freight recordkeeping law, after which they become eligible for deletion. We give the exact date that clock runs out.

This works because it honors the deletion right (Section 7.4) while being honest about the legal retention exception (Section 7.3), verifies before acting to avoid an account-takeover, and gives a concrete date rather than a vague "we can't."

---

## 14. Policy FAQ — Common Edge Cases

These are the questions Support and Legal field most often. Each answer points to the governing section.

**A customer asks for a refund on day 35. What do we do?** The 30-day window has passed (Section 8.1), so a refund is not owed. We say so plainly, offer to cancel future billing so they are not charged again, and never pretend a discretionary exception is a policy. A genuine goodwill exception is a manager's call, made explicitly as an exception, not dressed up as the rule.

**A customer wants their data in our EU region but signed up in North America. Can we move it?** Region is set at provisioning and never changed silently (Section 7.5), but a deliberate, documented migration is possible. It goes through the documented transfer mechanism with the customer's written instruction; it is never a quiet background change.

**An agent isn't sure whether something counts as a delay or a failure.** Use "delay" for any in-progress state and "failed" only when the shipment definitively will not arrive as planned (Section 4.3). When unsure, "delay" is the safer word because it does not assign blame or finality the facts have not yet earned.

**Someone from the press DMs an employee for a quick comment.** Route it to Communications the same business day and do not reply, not even "no comment" (Section 9.1). One company, one voice.

**A customer posts a glowing review naming their company.** We may not repost it publicly without their written permission (Section 9.6), because the shipment relationship is itself confidential (Section 9.2) — a public thank-you can expose who ships with us.

**An Enterprise account is past due. Do we cut them off?** Not without a human conversation first (Section 8.6). Suspension for non-payment never happens to an Enterprise account before a person at Meridian has spoken to a person at the customer.

**A teammate pasted a customer contract into an unapproved AI tool.** Treat it as a data-handling incident: report it, and because the data left our controls, the affected customer's exposure is assessed under the breach process (Sections 6.5 and 7.6). The honest, fast report is rewarded, not punished.

---

## 15. Quick Reference Card

When in doubt, these are the rules that catch the most mistakes:

1. Clarity beats cleverness, every time.
2. Serial comma, always. Sentence-case headings and buttons.
3. "Shipment," "carrier," "customer," "delay" — not "load," "trucker," "user," "late."
4. Never "seamless," "revolutionary," "simply," or "just."
5. Status is never color alone — always pair with an icon or label.
6. Refunds: full within 30 days; the one exception is delivered usage overage.
7. SLA: 99.9% monthly uptime for Business and Enterprise; credits up to 50%.
8. Passwords: 14+ characters, rotate every 90 days for Confidential or Restricted access.
9. No payment, credential, or access change on an email alone — verify on a second channel.
10. Breach notice to affected customers within 72 hours of confirmation.
11. When this document and a local guideline conflict, this document wins — and tell the Brand Council.
