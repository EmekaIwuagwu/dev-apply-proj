# APPROVED_PORTALS - Only CAPTCHA-free sources scraped or applied
APPROVED_PORTALS = [
    {
        "name": "LinkedIn Jobs",
        "base_url": "https://www.linkedin.com/jobs",
        "search_url": "https://www.linkedin.com/jobs/search/?keywords={query}&location={location}&f_TPR=r86400",
        "apply_type": "easy_apply_or_external",
        "captcha_risk": "low"
    },
    {
        "name": "Indeed",
        "base_url": "https://www.indeed.com",
        "search_url": "https://www.indeed.com/jobs?q={query}&l={location}&fromage=1",
        "apply_type": "indeed_apply_or_external",
        "captcha_risk": "low"
    },
    {
        "name": "Jobspresso",
        "base_url": "https://jobspresso.co",
        "search_url": "https://jobspresso.co/remote-work/#{query}",
        "apply_type": "external_link",
        "captcha_risk": "none"
    },
    {
        "name": "We Work Remotely",
        "base_url": "https://weworkremotely.com",
        "search_url": "https://weworkremotely.com/remote-jobs/search?term={query}",
        "apply_type": "external_email_or_form",
        "captcha_risk": "none"
    },
    {
        "name": "Remote OK",
        "base_url": "https://remoteok.com",
        "search_url": "https://remoteok.com/remote-{query}-jobs",
        "apply_type": "external_link",
        "captcha_risk": "none"
    },
    {
        "name": "Lever (Direct ATS)",
        "base_url": "https://jobs.lever.co",
        "search_url": None,
        "apply_type": "lever_form",
        "captcha_risk": "none"
    },
    {
        "name": "Ashby ATS",
        "base_url": "https://jobs.ashbyhq.com",
        "search_url": None,
        "apply_type": "ashby_form",
        "captcha_risk": "none"
    }
]

# Explicitly BLOCKED portals — never scrape or apply via these
BLOCKED_PORTALS = [
    {
        "name": "Greenhouse",
        "base_url": "https://boards.greenhouse.io",
        "reason": "Frequently presents reCAPTCHA v3 + v2 challenges."
    },
    {
        "name": "Workable",
        "base_url": "https://apply.workable.com",
        "reason": "Known to serve hCaptcha and detect automation."
    },
    {
        "name": "Workday",
        "base_url": "https://myworkdayjobs.com",
        "reason": "Requires account creation, OTP email codes, and has anti-automation measures."
    }
]
