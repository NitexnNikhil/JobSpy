import pandas as pd
from jobspy import scrape_jobs   

def main():
    jobs = scrape_jobs(
        site_name=["linkedin"],
        search_term="software engineer",
        location="Bengaluru, Karnataka",
        results_wanted=5,
        hours_old=72,
        verbose=2,
    )

    print(f"Found {jobs['job_count']} jobs")

    df = pd.DataFrame(jobs["jobs"])
    print(df.head())

    # Optional: save files
    df.to_csv("jobs.csv", index=False)

    import json
    with open("jobs.json", "w") as f:
        json.dump(jobs, f, indent=2)


if __name__ == "__main__":
    main()