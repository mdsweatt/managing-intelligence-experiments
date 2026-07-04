[Raw project notes — Project Atlas, week of June 24]

- Auth-service migration: finished moving 3 of 5 microservices to the new identity provider. The two remaining (billing, notifications) are more entangled than expected.
- Blocker: the notifications service has a hard dependency on the old auth tokens; needs a refactor before it can migrate. Est. one extra week.
- Performance: new login flow is ~200ms faster on average. QA signed off on the migrated services.
- Team: Priya out next week (vacation); Marcus picking up her review load.
- Budget: on track; ~62% of allocated hours used, ~55% through the timeline.
- Risk: the billing migration touches the payments path — we want a staged rollout with a rollback plan before starting.
- Next: start billing-migration design; refactor the notifications auth dependency; schedule a rollback rehearsal.
- Stakeholder demo of the new login flow went well; leadership asked when the full cutover completes — estimate was 3 weeks, now 4 given the notifications blocker.
