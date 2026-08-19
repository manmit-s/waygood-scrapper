# Waygood — Data Extraction Pipeline

A modular, production-style web-scraping pipeline that converts public
university/course pages into strictly-typed JSON datasets for the Waygood
study-abroad comparison platform.

## Repository layout
```
university.json     # 1 university record (official schema, 20 keys)
courses.json        # 2 course records   (official schema, 24 keys each)
scraper.py          # requests + BeautifulSoup pipeline
judgment.md         # extraction judgment calls (null discipline)
approach_note.md    # scaling & LLM-hallucination guardrails
requirements.txt    # pinned dependencies
README.md           # this file
```

## Setup & run
```bash
pip install -r requirements.txt
python scraper.py        # fetches targets and writes both JSON files
```

## Output schema

### `university.json` (20 keys)
`universityName`, `universityWebsite`, `universityInfo`, `countryName`,
`cityName`, `universityType` (`"PUBLIC"`), `stateName`, `addressLine1`,
`qsRanking`, `theRanking`, `usRanking`, `courseLevel`, `OpenIntakesYears`,
`OpenIntakesMonths`, `TotalEstimatedPerYearText`, `applicationFeeWaived`,
`logoImage`, `bannerImage`, `sourceUrl`, `lastVerifiedDate`.

### `courses.json` (24 keys per record)
`universityName`, `campusName`, `courseName`, `courseLevel`
(`"Masters"`/`"Bachelors"`), `attendanceType` (`"FULL-TIME"`/`"PART-TIME"`),
`firstYearTuitionFees` (`{currency, amount}`), `totalTuitionFee`,
`applicationFeeWaived` (`false`), `applicationFeeAmount`, `intakeYears`
(`[{"year":2026,"month":[...]}]`), `entry_requirements`, `courseDescription`,
`courseSubDiscipline`, `courseTaughtLanguages`, `duration` (published string),
`durationInMonths` (numeric conversion), `courseURL`,
`internationalApplicationDeadline`, `domesticApplicationDeadline`,
`requiredDocuments` (`[]`), `careerOpportunities`, `acceptanceRate`,
`sourceUrl`, `lastVerifiedDate`.

## Discipline rules (enforced)
- **Null discipline:** any field absent from the source page is `null` (or the
  schema default `false` / `[]`); never `""`, `"N/A"`, or a guessed/computed value.
- **Currencies:** ISO 4217 codes (`GBP`, `AED`, `USD`, `EUR`) — no symbols.
- **Fees:** exactly `{ "currency": "AED", "amount": 155483 }`.
- **Dates:** ISO 8601 (`YYYY-MM-DD`); `lastVerifiedDate` is the scrape date.
- **Exact match:** `universityName` is stored verbatim and matches across files.

## Code architecture (`scraper.py`)
- `clean_text` — strips HTML/whitespace/newlines.
- `extract_fee` — regex `£28,750` / `AED 155,483` → `{currency, amount}`.
- `_get_soup` — polite GET (custom `User-Agent`, 20s timeout).
- `_section_text` — pulls a section's text and de-duplicates repeats.
- `scrape_university` / `scrape_course` — return schema-shaped dicts.
- `main` — processes the 3 targets and writes both JSON files.

## Multi-institution note
The two course URLs belong to different institutions (University of Birmingham
Dubai and Heriot-Watt University Dubai). To honour null discipline, each course
keeps its real `universityName` verbatim; in production this becomes a
`universities` collection keyed by `universityId`, with the exact-match rule
validated within each university group.

## Known limitation
`_get_soup` currently raises on HTTP errors (e.g. transient `502`). A production
runner should add retry/backoff around the fetch.
