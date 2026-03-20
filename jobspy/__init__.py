# from __future__ import annotations

# from concurrent.futures import ThreadPoolExecutor, as_completed
# from typing import Tuple

# import pandas as pd

# from jobspy.bayt import BaytScraper
# from jobspy.bdjobs import BDJobs
# from jobspy.glassdoor import Glassdoor
# from jobspy.google import Google
# from jobspy.indeed import Indeed
# from jobspy.linkedin import LinkedIn
# from jobspy.naukri import Naukri
# from jobspy.model import JobType, Location, JobResponse, Country
# from jobspy.model import SalarySource, ScraperInput, Site
# from jobspy.util import (
#     set_logger_level,
#     extract_salary,
#     create_logger,
#     get_enum_from_value,
#     map_str_to_site,
#     convert_to_annual,
#     desired_order,
# )
# from jobspy.ziprecruiter import ZipRecruiter


# # Update the SCRAPER_MAPPING dictionary in the scrape_jobs function

# def scrape_jobs(
#     site_name: str | list[str] | Site | list[Site] | None = None,
#     search_term: str | None = None,
#     google_search_term: str | None = None,
#     location: str | None = None,
#     distance: int | None = 50,
#     is_remote: bool = False,
#     job_type: str | None = None,
#     easy_apply: bool | None = None,
#     results_wanted: int = 15,
#     country_indeed: str = "usa",
#     proxies: list[str] | str | None = None,
#     ca_cert: str | None = None,
#     description_format: str = "markdown",
#     linkedin_fetch_description: bool | None = False,
#     linkedin_company_ids: list[int] | None = None,
#     offset: int | None = 0,
#     hours_old: int = None,
#     enforce_annual_salary: bool = False,
#     verbose: int = 0,
#     user_agent: str = None,
#     **kwargs,
# ) -> pd.DataFrame:
#     """
#     Scrapes job data from job boards concurrently
#     :return: Pandas DataFrame containing job data
#     """
#     SCRAPER_MAPPING = {
#         Site.LINKEDIN: LinkedIn,
#         Site.INDEED: Indeed,
#         Site.ZIP_RECRUITER: ZipRecruiter,
#         Site.GLASSDOOR: Glassdoor,
#         Site.GOOGLE: Google,
#         Site.BAYT: BaytScraper,
#         Site.NAUKRI: Naukri,
#         Site.BDJOBS: BDJobs,  # Add BDJobs to the scraper mapping
#     }
#     set_logger_level(verbose)
#     job_type = get_enum_from_value(job_type) if job_type else None

#     def get_site_type():
#         site_types = list(Site)
#         if isinstance(site_name, str):
#             site_types = [map_str_to_site(site_name)]
#         elif isinstance(site_name, Site):
#             site_types = [site_name]
#         elif isinstance(site_name, list):
#             site_types = [
#                 map_str_to_site(site) if isinstance(site, str) else site
#                 for site in site_name
#             ]
#         return site_types

#     country_enum = Country.from_string(country_indeed)

#     scraper_input = ScraperInput(
#         site_type=get_site_type(),
#         country=country_enum,
#         search_term=search_term,
#         google_search_term=google_search_term,
#         location=location,
#         distance=distance,
#         is_remote=is_remote,
#         job_type=job_type,
#         easy_apply=easy_apply,
#         description_format=description_format,
#         linkedin_fetch_description=linkedin_fetch_description,
#         results_wanted=results_wanted,
#         linkedin_company_ids=linkedin_company_ids,
#         offset=offset,
#         hours_old=hours_old,
#     )

#     def scrape_site(site: Site) -> Tuple[str, JobResponse]:
#         scraper_class = SCRAPER_MAPPING[site]
#         scraper = scraper_class(proxies=proxies, ca_cert=ca_cert, user_agent=user_agent)
#         scraped_data: JobResponse = scraper.scrape(scraper_input)
#         cap_name = site.value.capitalize()
#         site_name = "ZipRecruiter" if cap_name == "Zip_recruiter" else cap_name
#         site_name = "LinkedIn" if cap_name == "Linkedin" else cap_name
#         create_logger(site_name).info(f"finished scraping")
#         return site.value, scraped_data

#     site_to_jobs_dict = {}

#     def worker(site):
#         site_val, scraped_info = scrape_site(site)
#         return site_val, scraped_info

#     with ThreadPoolExecutor() as executor:
#         future_to_site = {
#             executor.submit(worker, site): site for site in scraper_input.site_type
#         }

#         for future in as_completed(future_to_site):
#             site_value, scraped_data = future.result()
#             site_to_jobs_dict[site_value] = scraped_data

#     jobs_dfs: list[pd.DataFrame] = []

#     for site, job_response in site_to_jobs_dict.items():
#         for job in job_response.jobs:
#             job_data = job.dict()
#             job_url = job_data["job_url"]
#             job_data["site"] = site
#             job_data["company"] = job_data["company_name"]
#             job_data["job_type"] = (
#                 ", ".join(job_type.value[0] for job_type in job_data["job_type"])
#                 if job_data["job_type"]
#                 else None
#             )
#             job_data["emails"] = (
#                 ", ".join(job_data["emails"]) if job_data["emails"] else None
#             )
#             if job_data["location"]:
#                 job_data["location"] = Location(
#                     **job_data["location"]
#                 ).display_location()

#             # Handle compensation
#             compensation_obj = job_data.get("compensation")
#             if compensation_obj and isinstance(compensation_obj, dict):
#                 job_data["interval"] = (
#                     compensation_obj.get("interval").value
#                     if compensation_obj.get("interval")
#                     else None
#                 )
#                 job_data["min_amount"] = compensation_obj.get("min_amount")
#                 job_data["max_amount"] = compensation_obj.get("max_amount")
#                 job_data["currency"] = compensation_obj.get("currency", "USD")
#                 job_data["salary_source"] = SalarySource.DIRECT_DATA.value
#                 if enforce_annual_salary and (
#                     job_data["interval"]
#                     and job_data["interval"] != "yearly"
#                     and job_data["min_amount"]
#                     and job_data["max_amount"]
#                 ):
#                     convert_to_annual(job_data)
#             else:
#                 if country_enum == Country.USA:
#                     (
#                         job_data["interval"],
#                         job_data["min_amount"],
#                         job_data["max_amount"],
#                         job_data["currency"],
#                     ) = extract_salary(
#                         job_data["description"],
#                         enforce_annual_salary=enforce_annual_salary,
#                     )
#                     job_data["salary_source"] = SalarySource.DESCRIPTION.value

#             job_data["salary_source"] = (
#                 job_data["salary_source"]
#                 if "min_amount" in job_data and job_data["min_amount"]
#                 else None
#             )

#             #naukri-specific fields
#             job_data["skills"] = (
#                 ", ".join(job_data["skills"]) if job_data["skills"] else None
#             )
#             job_data["experience_range"] = job_data.get("experience_range")
#             job_data["company_rating"] = job_data.get("company_rating")
#             job_data["company_reviews_count"] = job_data.get("company_reviews_count")
#             job_data["vacancy_count"] = job_data.get("vacancy_count")
#             job_data["work_from_home_type"] = job_data.get("work_from_home_type")

#             job_df = pd.DataFrame([job_data])
#             jobs_dfs.append(job_df)

#     if jobs_dfs:
#         # Step 1: Filter out all-NA columns from each DataFrame before concatenation
#         filtered_dfs = [df.dropna(axis=1, how="all") for df in jobs_dfs]

#         # Step 2: Concatenate the filtered DataFrames
#         jobs_df = pd.concat(filtered_dfs, ignore_index=True)

#         # Step 3: Ensure all desired columns are present, adding missing ones as empty
#         for column in desired_order:
#             if column not in jobs_df.columns:
#                 jobs_df[column] = None  # Add missing columns as empty

#         # Reorder the DataFrame according to the desired order
#         jobs_df = jobs_df[desired_order]

#         # Step 4: Sort the DataFrame as required
#         return jobs_df.sort_values(
#             by=["site", "date_posted"], ascending=[True, False]
#         ).reset_index(drop=True)
#     else:
#         return pd.DataFrame()


# # Add BDJobs to __all__
# __all__ = [
#     "BDJobs",
# ]



from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple
import pandas as pd

from jobspy.bayt import BaytScraper
from jobspy.bdjobs import BDJobs
from jobspy.glassdoor import Glassdoor
from jobspy.google import Google
from jobspy.indeed import Indeed
from jobspy.linkedin import LinkedIn
from jobspy.naukri import Naukri
from jobspy.ziprecruiter import ZipRecruiter

from jobspy.model import JobType, Location, JobResponse, Country
from jobspy.model import SalarySource, ScraperInput, Site

from jobspy.util import (
    set_logger_level,
    extract_salary,
    create_logger,
    get_enum_from_value,
    map_str_to_site,
    convert_to_annual,
)

# ✅ FINAL FIELD ORDER
FINAL_COLUMNS = [
    "id","site","job_url","job_url_direct","title","company","location",
    "date_posted","job_type","salary_source","interval","min_amount",
    "max_amount","currency","is_remote","job_level","job_function",
    "listing_type","emails","description","company_industry",
    "company_url","company_logo","company_url_direct",
    "company_addresses","company_num_employees","company_revenue",
    "company_description","skills","experience_range",
    "company_rating","company_reviews_count","vacancy_count",
    "work_from_home_type"
]


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
    linkedin_fetch_description=True,   # 🔥 ENABLED
    linkedin_company_ids=None,
    offset=0,
    hours_old=None,
    enforce_annual_salary=False,
    verbose=0,
    user_agent=None,
) -> pd.DataFrame:

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
        elif isinstance(site_name, Site):
            return [site_name]
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

    # ✅ Parallel scraping
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
            # ✅ NORMALIZATION
            # =========================
            job_data["site"] = site
            job_data["company"] = job_data.get("company_name")
            job_data["job_url_direct"] = job_data.get("job_url_direct") or job_data.get("job_url")

            # job_type
            job_data["job_type"] = (
                ", ".join(j.value[0] for j in job_data.get("job_type", []))
                if job_data.get("job_type") else None
            )

            # emails
            job_data["emails"] = ", ".join(job_data["emails"]) if job_data.get("emails") else None

            # location
            if job_data.get("location"):
                job_data["location"] = Location(**job_data["location"]).display_location()

            # =========================
            # ✅ DESCRIPTION FIX
            # =========================
            if not job_data.get("description"):
                job_data["description"] = (
                    job_data.get("summary") or job_data.get("title") or "Not Available"
                )

            # =========================
            # ✅ COMPANY DATA
            # =========================
            job_data["company_industry"] = job_data.get("company_industry") or "Unknown"
            job_data["company_description"] = job_data.get("company_description")
            job_data["company_logo"] = job_data.get("company_logo")
            job_data["company_url"] = job_data.get("company_url")
            job_data["company_url_direct"] = job_data.get("company_url_direct")

            # =========================
            # ✅ JOB META
            # =========================
            job_data["job_level"] = job_data.get("job_level") or "Not Specified"
            job_data["job_function"] = job_data.get("job_function") or "Engineering"
            job_data["listing_type"] = job_data.get("listing_type") or "Standard"

            # =========================
            # ✅ COMPENSATION
            # =========================
            comp = job_data.get("compensation")
            if comp and isinstance(comp, dict):
                job_data["interval"] = comp.get("interval").value if comp.get("interval") else None
                job_data["min_amount"] = comp.get("min_amount")
                job_data["max_amount"] = comp.get("max_amount")
                job_data["currency"] = comp.get("currency", "USD")
                job_data["salary_source"] = SalarySource.DIRECT_DATA.value
            else:
                job_data["interval"] = None
                job_data["min_amount"] = None
                job_data["max_amount"] = None
                job_data["currency"] = None
                job_data["salary_source"] = None

            # =========================
            # ✅ NAUKRI FIELDS
            # =========================
            job_data["skills"] = ", ".join(job_data["skills"]) if job_data.get("skills") else None

            exp = job_data.get("experience_range")
            if isinstance(exp, dict):
                job_data["experience_range"] = f"{exp.get('min')} - {exp.get('max')} years"

            job_data["company_rating"] = job_data.get("company_rating")
            job_data["company_reviews_count"] = job_data.get("company_reviews_count")
            job_data["vacancy_count"] = job_data.get("vacancy_count")
            job_data["work_from_home_type"] = job_data.get("work_from_home_type")

            # =========================
            # ✅ ENSURE ALL COLUMNS
            # =========================
            for col in FINAL_COLUMNS:
                if col not in job_data:
                    job_data[col] = None

            jobs_list.append(job_data)

    # =========================
    # ✅ FINAL DATAFRAME
    # =========================
    if not jobs_list:
        return pd.DataFrame(columns=FINAL_COLUMNS)

    df = pd.DataFrame(jobs_list)

    df = df[FINAL_COLUMNS]

    return df.sort_values(
        by=["site", "date_posted"],
        ascending=[True, False]
    ).reset_index(drop=True)