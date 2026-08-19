# Judgment Calls — Null Discipline in Practice

## 1. A field I could not find
I could not find an explicit **medium of instruction / `courseTaughtLanguages`**
for either course. Before marking it `null` I inspected the rendered DOM (course
sidebar, "Key information" block, and `<meta>` tags), searched the full page text
for "taught in", "medium of instruction", and "language of study", and checked the
linked English-requirements portal. None stated the delivery language as fact, so
the field is `null` rather than assumed to be English.

## 2. Two numbers for the same thing
The Birmingham MSc page shows **AED 155,483 (full-time)** and **AED 77,742
(part-time)**. I did not average them or silently pick one. The published
duration string (`"1 year full-time; 2 years part-time"`) is kept verbatim in
`duration`, and `durationInMonths` is derived only for the unambiguous 1-year
full-time case (12). The two fee figures live in distinct, schema-typed fields
(`firstYearTuitionFees` + a part-time capture) so downstream consumers can filter
by mode instead of losing information.

## 3. "Waived" vs "unstated" application fee
I distinguish them by explicit wording, never by omission. If a page stated "no
application fee" / "free to apply", I would record `applicationFeeWaived: true`
with `applicationFeeAmount: 0`. If the fee is simply absent, both are `null` /
`false` — meaning *unknown/unstated*, not *free*. Both target pages omit the
field, so `applicationFeeWaived` is `false` and `applicationFeeAmount` is `null`.
A `null` and a `false` carry different meaning for ranking and filtering, so they
are never collapsed.
