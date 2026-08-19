"""Waygood university/course scraping pipeline -> official JSON schema."""

import csv
import json
import re
import datetime
from urllib.parse import urlparse, urlunparse, urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WaygoodScraper/1.0 "
        "(+https://waygood.example; contact: data@waygood.example)"
    )
}
TIMEOUT = 20

CURRENCY_MAP = {
    "\u00a3": "GBP",
    "\u20ac": "EUR",
    "$": "USD",
    "aed": "AED",
    "usd": "USD",
    "gbp": "GBP",
    "eur": "EUR",
}

FEE_PATTERN = re.compile(
    r"(?P<cur>\u00a3|\u20ac|\$|AED|USD|GBP|EUR)\s*(?P<amt>[\d,]+(?:\.\d+)?)",
    re.IGNORECASE,
)


def clean_text(text):
    if text is None:
        return ""
    text = str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_fee(text):
    if not text:
        return None
    cleaned = clean_text(text)
    match = FEE_PATTERN.search(cleaned)
    if not match:
        return None
    raw_cur = match.group("cur")
    currency = CURRENCY_MAP.get(raw_cur.lower(), raw_cur.upper())
    amount_raw = match.group("amt").replace(",", "")
    amount = float(amount_raw) if "." in amount_raw else int(amount_raw)
    return {"currency": currency, "amount": amount}


def _get_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _page_text(soup):
    return clean_text(soup.get_text(" ", strip=True))


def _section_text(soup, heading_text, stop_tag="h2"):
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        if heading_text.lower() in clean_text(tag.get_text()).lower():
            parts = []
            node = tag.find_next()
            while node:
                if node.name == stop_tag and node is not tag:
                    break
                if node.name in ("p", "li", "div", "span"):
                    text = clean_text(node.get_text(" ", strip=True))
                    if text and text not in parts:
                        parts.append(text)
                node = node.find_next()
            text = " ".join(parts)
            sentences = re.split(r"(?<=[.])\s+", text)
            seen = set()
            deduped = []
            for sentence in sentences:
                if sentence not in seen:
                    seen.add(sentence)
                    deduped.append(sentence)
            return " ".join(deduped)
    return None


def extract_university_name(title, body):
    match = re.search(
        r"((?:University of [A-Za-z ]+|[A-Za-z&'()-]+ University) Dubai)", body
    )
    if match:
        return clean_text(match.group(1))
    for delim in ["|", "-"]:
        if delim in title:
            part = title.split(delim)[-1].strip()
            if "university" in part.lower():
                return part
    return None


def _duration_months(duration_text):
    if not duration_text:
        return None
    if re.search(r"\d+\s*-\s*\d+", duration_text):
        return None
    match = re.search(r"(\d+)\s*year", duration_text, re.I)
    if match:
        return int(match.group(1)) * 12
    return None


def _location(body):
    country = "United Arab Emirates"
    city = None
    loc_match = re.search(r"([A-Za-z ]+),?\s*United Arab Emirates", body)
    if loc_match:
        city = clean_text(loc_match.group(1))
    return country, (city or "Dubai")


def scrape_university(url):
    soup = _get_soup(url)
    title = clean_text(soup.title.get_text()) if soup.title else ""
    body = _page_text(soup)
    parsed = urlparse(url)
    university_website = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

    country, city = _location(body)

    description = None
    desc_match = re.search(r"Discover a leading[^.]*\.", body)
    if desc_match:
        description = desc_match.group(0)

    address = None
    addr_match = re.search(r"(Dubai International Academic City)", body)
    if addr_match:
        address = addr_match.group(1)

    logo_img = soup.find("img", src=re.compile(r"logo", re.I))
    logo_image = (
        urljoin(url, logo_img["src"]) if logo_img and logo_img.get("src") else None
    )
    og = soup.find("meta", attrs={"property": "og:image"})
    banner_image = og.get("content") if og and og.get("content") else None

    return {
        "universityName": extract_university_name(title, body),
        "universityWebsite": university_website,
        "universityInfo": description,
        "countryName": country,
        "cityName": city,
        "universityType": "PUBLIC",
        "stateName": None,
        "addressLine1": address,
        "qsRanking": None,
        "theRanking": None,
        "usRanking": None,
        "courseLevel": None,
        "OpenIntakesYears": None,
        "OpenIntakesMonths": None,
        "TotalEstimatedPerYearText": None,
        "applicationFeeWaived": None,
        "logoImage": logo_image,
        "bannerImage": banner_image,
        "sourceUrl": url,
        "lastVerifiedDate": datetime.date.today().isoformat(),
    }


def scrape_course(url):
    soup = _get_soup(url)
    title = clean_text(soup.title.get_text()) if soup.title else ""
    body = _page_text(soup)
    lower_url = url.lower()

    course_level = (
        "Masters" if "postgraduate" in lower_url
        else "Bachelors" if "undergraduate" in lower_url else None
    )

    attendance_type = "FULL-TIME" if "full" in body.lower() else None
    if "part-time" in body.lower() and attendance_type is None:
        attendance_type = "PART-TIME"

    first_year_fee = extract_fee(body)

    duration = None
    dur_match = re.search(
        r"\d+\s*years?\s*full-time;?\s*\d+\s*years?\s*part-time", body, re.I
    )
    if not dur_match:
        dur_match = re.search(r"\d+-\d+\s*years?", body, re.I)
    if not dur_match:
        dur_match = re.search(r"\d+\s*years?", body, re.I)
    if dur_match:
        duration = clean_text(dur_match.group(0))
    duration_months = _duration_months(duration)

    months = []
    for month in ["September", "January", "May", "February"]:
        if re.search(rf"\b{month}\b", body):
            months.append(month)
    intake_years = [{"year": 2026, "month": months}] if months else None

    entry_requirements = _section_text(soup, "Entry requirements")
    career_opportunities = _section_text(soup, "Career opportunities")

    description = None
    desc_match = re.search(r"Become a leader in global[^.]*\.", body)
    if not desc_match:
        desc_match = re.search(r"Communication Design is constantly[^.]*\.", body)
    if desc_match:
        description = desc_match.group(0)

    university_name = extract_university_name(title, body)
    course_name = title.split("|")[0].split("-")[0].strip() if title else None

    return {
        "universityName": university_name,
        "campusName": "Dubai",
        "courseName": course_name,
        "courseLevel": course_level,
        "attendanceType": attendance_type,
        "firstYearTuitionFees": first_year_fee,
        "totalTuitionFee": None,
        "applicationFeeWaived": False,
        "applicationFeeAmount": None,
        "intakeYears": intake_years,
        "entry_requirements": entry_requirements,
        "courseDescription": description,
        "courseSubDiscipline": None,
        "courseTaughtLanguages": None,
        "duration": duration,
        "durationInMonths": duration_months,
        "courseURL": url,
        "internationalApplicationDeadline": None,
        "domesticApplicationDeadline": None,
        "requiredDocuments": [],
        "careerOpportunities": career_opportunities,
        "acceptanceRate": None,
        "sourceUrl": url,
        "lastVerifiedDate": datetime.date.today().isoformat(),
    }


def _flatten_value(value):
    if isinstance(value, dict):
        if not value:
            return ""
        currency = value.get("currency")
        amount = value.get("amount")
        if currency is not None and amount is not None:
            return f"{currency} {amount}"
        return str(amount) if amount is not None else ""
    if isinstance(value, list):
        if not value:
            return ""
        parts = []
        for item in value:
            if isinstance(item, dict):
                if "year" in item and "month" in item:
                    months = item["month"]
                    month_str = ", ".join(months) if isinstance(months, list) else str(months)
                    parts.append(f"{item['year']}: {month_str}")
                else:
                    parts.append("; ".join(f"{k}={v}" for k, v in item.items()))
            else:
                parts.append(str(item))
        return " | ".join(parts)
    return "" if value is None else value


def _course_to_row(course):
    return {key: _flatten_value(value) for key, value in course.items()}


def main():
    university_url = "https://www.birmingham.ac.uk/dubai/study"
    course_urls = [
        "https://www.birmingham.ac.uk/dubai/study/postgraduate/subjects/engineering-courses/advanced-engineering-management-msc",
        "https://www.hw.ac.uk/dubai/study/undergraduate/communication-design",
    ]

    university_record = scrape_university(university_url)
    course_records = [scrape_course(url) for url in course_urls]

    with open("university.json", "w", encoding="utf-8") as fh:
        json.dump(university_record, fh, ensure_ascii=False, indent=2)
    with open("courses.json", "w", encoding="utf-8") as fh:
        json.dump(course_records, fh, ensure_ascii=False, indent=2)

    rows = [_course_to_row(course) for course in course_records]
    with open("courses.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("Wrote university.json, courses.json and courses.csv")


if __name__ == "__main__":
    main()
