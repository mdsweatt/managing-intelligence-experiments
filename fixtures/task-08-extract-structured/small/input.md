POST-INCIDENT REVIEW — CHECKOUT LATENCY DEGRADATION
Northwind Logistics Platform · Site Reliability Engineering

This document is the post-incident review for a single customer-impacting production incident on the Northwind shipping and fulfillment platform. It follows the standard review format used by the Site Reliability Engineering team and was completed within five business days of resolution. Severity follows the internal scale, where SEV1 is a full or near-full outage of a revenue path, SEV2 is significant degradation with a workaround, SEV3 is a contained fault with limited blast radius, and SEV4 is a minor defect logged for completeness.

Incident identifier. The incident carries the stable identifier INC4101.

Detection. The incident was detected on the first of August, 2026, at 02:14 UTC by the automated latency monitor on the checkout service. The monitor fired when the ninety-fifth-percentile response time on the order-submission endpoint crossed its alerting threshold of one second sustained over two minutes. Detection was therefore automated rather than customer-reported, which is the desired path; no customer tickets were filed before the monitor paged, indicating the alert threshold is well calibrated for this endpoint. The page was routed to the primary on-call rotation for the checkout service.

Severity. The incident was classified as SEV2. It was held at SEV2 rather than SEV1 because, although checkout was significantly degraded, order submissions were still completing on client retry and no revenue path was fully unavailable.

Response. The on-call engineer, Priya Raman, acknowledged the page within three minutes of it firing and led the response. No incident commander was engaged because the incident remained at SEV2 and was resolved quickly; the on-call engineer handled coordination directly.

Root cause. The root cause was connection-pool exhaustion on the primary orders database. A scheduled analytics job opened several hundred long-lived read connections against the primary database and failed to release them, consuming the connection pool that the order-submission path depended on. As the pool drained, order-submission requests queued waiting for a connection, driving the ninety-fifth-percentile response time from a baseline of roughly 180 milliseconds to roughly 2.3 seconds over a four-minute window.

Customer impact. Checkout was degraded for approximately twenty-six minutes. During that window an estimated 1,400 order submissions were retried by the client before succeeding, and roughly 90 submissions were abandoned by customers who did not retry. No orders were lost in a way that prevented later completion, and no data was corrupted; the impact was latency and abandonment rather than failure. The affected endpoint serves all geographic regions, so impact was global rather than confined to one region, although the overnight timing in the primary market limited the absolute number of affected customers compared with a peak-hour occurrence.

Mitigation. The responding engineer terminated the runaway analytics database session, which immediately began returning connections to the pool, and temporarily raised the connection-pool ceiling to absorb the recovery. Order-submission latency returned to baseline within a few minutes of the session being terminated.

Resolution. The incident was resolved on the first of August, 2026, at 02:51 UTC, when latency had returned to baseline and remained stable for a confirmation period. The total duration from detection to resolution was thirty-seven minutes.

Corrective action. The committed corrective action is to move the analytics job off the primary database and onto a dedicated read replica so that analytics workloads can never again contend for the order path's connections, and to add a hard cap on connection lifetime so that no single session can hold connections indefinitely. This corrective action is owned by the Data Platform team and is targeted for completion by the fifteenth of August, 2026.

Follow-up. A follow-up check is scheduled to confirm the corrective action has shipped and that the analytics job no longer touches the primary database. The reviewer notes that the connection-pool ceiling increase was a temporary mitigation only and must be reverted once the analytics job has been moved, so that the pool size reflects genuine demand rather than the emergency headroom added during the incident.
