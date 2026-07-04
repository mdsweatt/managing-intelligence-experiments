# Memorandum: Consolidating the Regional Vendor Onboarding Process

**To:** Operations Leadership Team
**From:** Procurement Operations
**Re:** Standardizing vendor onboarding across the three regional hubs

Over the past two quarters, the time required to bring a new supplier from initial contract signature to first usable purchase order has grown from an average of eleven business days to nineteen. This memo summarizes what we found when we traced the delay, and recommends a consolidated onboarding workflow to replace the three divergent processes currently run by the East, Central, and West hubs.

## What we observed

Each hub developed its onboarding sequence independently, and the differences are now the primary source of friction. The East hub collects tax and banking documentation up front but defers compliance screening until after the contract is countersigned, which means a supplier can clear most of the process only to be blocked at the final gate. The Central hub runs compliance first but uses a manual spreadsheet to track document status, so requests routinely stall when the owning analyst is on leave. The West hub has the fastest median time but achieves it by skipping the secondary approval on purchases under a set threshold, which has produced two audit exceptions in the last year.

When a supplier sells to more than one region, the problem compounds. We currently re-onboard the same vendor separately in each hub, duplicating document collection and creating conflicting master records. Finance has flagged eleven vendors that exist under slightly different legal names across our systems, which complicates spend analysis and weakens our negotiating position at renewal.

## Why the delay grew

Three factors account for most of the increase. First, volume rose roughly thirty percent year over year without a matching increase in onboarding staff, so queues lengthened. Second, a tightened compliance policy added a sanctions-screening step that no hub had fully automated, adding two to four days per vendor. Third, the handoffs between procurement, legal, and finance rely on email rather than a shared system of record, so status is opaque and items fall through the cracks.

## Recommendation

We propose a single onboarding workflow, owned centrally, with regional intake preserved only for relationship continuity. The core of the proposal is a fixed sequence with clear gates: intake and document collection, automated compliance and sanctions screening, legal review, finance setup, and final activation. Each gate has a named owner and a service-level target, and a request cannot advance until the prior gate is cleared.

To support this, we recommend adopting a shared onboarding tracker visible to all three functions, replacing the Central hub spreadsheet and the scattered email threads. The tracker should enforce a single master vendor record, so a supplier selling into multiple regions is onboarded once and linked to each region rather than duplicated. We also recommend automating the sanctions screen through our existing compliance vendor's API, which testing suggests would remove most of the two-to-four-day manual step.

## Expected impact

If adopted, we estimate the consolidated workflow returns the median onboarding time to roughly ten business days within one quarter, with a tighter spread than any hub achieves today. Eliminating duplicate records should also recover meaningful analyst time currently spent reconciling vendor master data, and it closes the audit gap created by the West hub's threshold shortcut, since the secondary approval becomes a non-skippable gate for every region.

## Risks and what we still need to decide

The main risk is transition disruption: in-flight onboardings will need to migrate to the new tracker, and the West hub will lose the speed it gained from skipping a control, which may generate pushback. We recommend grandfathering only the suppliers already past the legal-review gate and routing everything earlier through the new sequence.

Two decisions remain open and need leadership input. First, whether central operations or the regional hubs hold final activation authority — we lean central for consistency, but regional leaders have argued that local context matters for activation timing. Second, the budget for the compliance API integration, which procurement can fund from this year's tooling allocation only if the analytics dashboard refresh slips a quarter.

## Requested next steps

We ask the leadership team to approve the consolidated workflow in principle at the next review, confirm the activation-authority decision, and authorize a four-week pilot in the Central hub, which has the highest current friction and the most to gain. Procurement will return with a measured before-and-after comparison from the pilot before any company-wide rollout, so the decision to scale rests on observed results rather than projection.
