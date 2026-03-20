from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple
import pandas as pd
import re
import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from jobspy.bayt import BaytScraper
from jobspy.bdjobs import BDJobs
from jobspy.glassdoor import Glassdoor
from jobspy.google import Google
from jobspy.indeed import Indeed
from jobspy.linkedin import LinkedIn
from jobspy.naukri import Naukri
from jobspy.ziprecruiter import ZipRecruiter

from jobspy.model import Location, JobResponse, Country
from jobspy.model import ScraperInput, Site

from jobspy.util import (
    set_logger_level,
    create_logger,
    get_enum_from_value,
    map_str_to_site,
)

# =========================
# LINKEDIN DESCRIPTION FETCH
# =========================
def fetch_linkedin_description(url: str) -> str:
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        match = re.search(r'"description":"(.*?)"', html)
        if match:
            return match.group(1)

    except Exception:
        pass

    return ""


# =========================
#  MAIN FUNCTION
# =========================
def scrape_jobs(
    site_name=None,
    search_term=None,
    google_search_term=None,
    location=None,
    distance=50,
    is_remote=False,
    job_type=None,
    easy_apply=None,
    results_wanted=15,
    country_indeed="India",
    proxies=None,
    ca_cert=None,
    description_format="markdown",
    linkedin_fetch_description=True,
    linkedin_company_ids=None,
    offset=0,
    hours_old=None,
    verbose=0,
    user_agent=None,
) -> dict:

    SCRAPER_MAPPING = {
        Site.LINKEDIN: LinkedIn,
        Site.INDEED: Indeed,
        Site.ZIP_RECRUITER: ZipRecruiter,
        Site.GLASSDOOR: Glassdoor,
        Site.GOOGLE: Google,
        Site.BAYT: BaytScraper,
        Site.NAUKRI: Naukri,
        Site.BDJOBS: BDJobs,
    }

    set_logger_level(verbose)
    job_type = get_enum_from_value(job_type) if job_type else None

    def get_sites():
        if isinstance(site_name, str):
            return [map_str_to_site(site_name)]
        elif isinstance(site_name, list):
            return [map_str_to_site(s) if isinstance(s, str) else s for s in site_name]
        return [Site.LINKEDIN]

    scraper_input = ScraperInput(
        site_type=get_sites(),
        country=Country.from_string(country_indeed),
        search_term=search_term,
        google_search_term=google_search_term,
        location=location,
        distance=distance,
        is_remote=is_remote,
        job_type=job_type,
        easy_apply=easy_apply,
        description_format=description_format,
        linkedin_fetch_description=linkedin_fetch_description,
        results_wanted=results_wanted,
        linkedin_company_ids=linkedin_company_ids,
        offset=offset,
        hours_old=hours_old,
    )

    def scrape_site(site: Site) -> Tuple[str, JobResponse]:
        scraper = SCRAPER_MAPPING[site](proxies=proxies, ca_cert=ca_cert, user_agent=user_agent)
        data = scraper.scrape(scraper_input)
        create_logger(site.value).info("finished scraping")
        return site.value, data

    # =========================
    # PARALLEL SCRAPING
    # =========================
    results = {}
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(scrape_site, s): s for s in scraper_input.site_type}
        for f in as_completed(futures):
            site, data = f.result()
            results[site] = data

    jobs_list = []

    for site, response in results.items():
        for job in response.jobs:
            job_data = job.dict()

            # =========================
            #  LOCATION FORMAT
            # =========================
            location_str = None
            if job_data.get("location"):
                location_str = Location(**job_data["location"]).display_location()

            # =========================
            # DESCRIPTION FIX
            # =========================
            description = job_data.get("description")

            if not description:
                if site == "linkedin":
                    description = fetch_linkedin_description(job_data.get("job_url"))

                if not description:
                    description = job_data.get("summary") or job_data.get("title") or ""

            # =========================
            # ATS STRUCTURE
            # =========================
            ats_job = {
                "provider": site,
                "job_id": job_data.get("id"),
                "title": job_data.get("title"),
                "location": location_str,
                "date_posted": str(job_data.get("date_posted") or ""),
                "absolute_job_url": job_data.get("job_url"),
                "source_site": job_data.get("company_url") or site,
                "description": description,
            }

            jobs_list.append(ats_job)

    # =========================
    # FINAL JSON STRUCTURE
    # =========================
    result = {
        "provider": "mixed" if len(results) > 1 else list(results.keys())[0],
        "source_url": location or "",
        "crawled_at_utc": datetime.now(timezone.utc).isoformat(),
        "job_count": len(jobs_list),
        "jobs": jobs_list,
    }

    return result


# =========================
# USAGE (JSON + CSV)
# =========================
if __name__ == "__main__":
    result = scrape_jobs(
        site_name=["linkedin", "indeed"],
        search_term="backend engineer",
        location="Bengaluru, Karnataka",
        results_wanted=20,
        hours_old=72,
        verbose=1,
    )

    # JSON OUTPUT
    with open("jobs.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # CSV OUTPUT
    df = pd.DataFrame(result["jobs"])
    df.to_csv("jobs.csv", index=False)