import csv

from jobspy import scrape_jobs


def main() -> None:
    # Edit these values to match the job search you want to run.
    jobs = scrape_jobs(
        site_name=["linkedin"],
        search_term="software engineer",
        location="Bengaluru, Karnataka",
        results_wanted=500,
        hours_old=24,
        country_indeed="India",
        verbose=2,
    )

    print(f"Found {len(jobs)} jobs")
    print(jobs.head())

    if not jobs.empty:
        jobs.to_csv(
            "jobs.csv",
            quoting=csv.QUOTE_NONNUMERIC,
            escapechar="\\",
            index=False,
        )
        print("Saved results to jobs.csv")


if __name__ == "__main__":
    main()
