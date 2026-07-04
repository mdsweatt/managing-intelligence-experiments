# Format Example — Subsystem Requirement Style Guide

Write each subsystem requirement using the structure shown below. The example items are from an unrelated feature (a payroll export service) and illustrate the required format only — do not reuse their content.

## SUB-PAY-001 — Export File Generation
Statement: The Payroll Export subsystem shall generate a payment file in the partner bank's published format for each approved pay run.
Rationale: The bank rejects files that deviate from its format, which would delay employee pay.
Acceptance criteria:
- Produces one payment entry per employee included in the approved pay run.
- File batch totals equal the approved pay-run total to the cent.
- Refuses to generate a file for a pay run that has not been approved.
Verification: Compare generated files against bank-validated reference files for three sample pay runs.

## SUB-PAY-002 — Invalid-Record Reporting
Statement: The Payroll Export subsystem shall list every employee record that fails format validation in a discrepancy report, while still exporting the remaining valid records.
Rationale: One malformed record must not delay pay for the rest of the company.
Acceptance criteria:
- Each rejected record appears in the report with the specific rule it violated.
- Valid records in the same pay run are exported unaffected.
- The report is available to payroll administrators before the payment file is transmitted.
Verification: Run a seeded pay run containing known-invalid records and inspect the report and the output file.

Follow this structure for every subsystem requirement you write: a unique ID, a short title, a single "shall" statement, a rationale, testable acceptance criteria, and a verification method. Decompose thoroughly: write at least twelve subsystem requirements — where the source bundles several capabilities into one obligation, split it into separate requirements — each with at least three acceptance criteria; the complete specification should run about 1,450 words (within ±10%).
