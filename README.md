# Planning update

Basic tool that grabs a summary of latest Oxford planning applications of interest from the weekly list. 

https://public.oxford.gov.uk/online-applications/search.do?action=weeklyList

## Basic features 

- CLI that grabs applications by:
  - Date (defaults to latest week)
  - Ward(s)
  - Parish
  - Keywords in the application description
  - Major applications listed on Oxford City Council's current major applications page
  - Going to an upcoming planning or planning review committee
- Produces summary with descriptions and links
- Config for preferences

## Current scraper

`main.py` fetches planning applications for the selected ward/parish filters
using the weekly list filters for `validated`, `decided`, or `both`.
When `keywords` are supplied, the scraper searches across all wards and parishes
for proposal text matches instead of applying ward/parish filters.
When `major = true` is supplied, the scraper also searches across all wards and
parishes, scrapes the live Oxford City Council major-applications page, and
keeps only weekly-list results whose `ApplicationRef` appears there.

The lookup data lives in [ward_mappings.json](/Users/annarailton/projects/planning-update/ward_mappings.json),
and [location_lookup.py](/Users/annarailton/projects/planning-update/location_lookup.py) loads it for the scraper.

By default it checks the latest week in the dropdown and falls back one week if there are
no results only if you explicitly select a different week. Otherwise it uses the latest
available week from the dropdown.

## Query flow

The scraper works in three stages:

1. Build the weekly-list search payload.
   `PlanningQuery` in [models.py](/Users/annarailton/projects/planning-update/models.py) resolves the optional human-readable ward and parish names to Oxford's internal codes and serializes the form payload for the selected week and mode (`validated` or `decided`). The CLI can also run `both`, which executes those two queries sequentially and renders them in separate sections.

2. Submit the weekly-list search and collect result pages.
   [scraper.py](/Users/annarailton/projects/planning-update/scraper.py) fetches the weekly-list form to get the CSRF token and available weeks, submits the query, and follows any pagination links so all result cards are collected rather than only the first page.

3. Enrich each result from the application detail pages.
   [parser.py](/Users/annarailton/projects/planning-update/parser.py) extracts the application reference, proposal, address, received date, and validated date from the weekly results. The scraper then fetches each application's summary page to get `status`, `decision`, and `decision issued date`, and fetches the `Important Dates` tab to get the consultation and determination deadlines.

## Setup with uv

Create a virtual environment and install dependencies:

```bash
uv venv
source .venv/bin/activate
uv sync
```

After that you can run the scraper with either the console script or Python directly.

If you want to send emails with `--email-to`, create a `.env` file in the project
root with your Resend API key:

```bash
RESEND_API_KEY=re_your_key_here
```

Example:

```bash
# Run with default settings
uv run oxford-weekly
# Save the rendered HTML locally instead of emailing
uv run oxford-weekly --debug
# Filter to one parish
uv run oxford-weekly --parish "Littlemore"
# Filter to one ward
uv run oxford-weekly --ward "churchill"
# Filter to multiple wards
uv run oxford-weekly --ward "churchill" --ward "hinksey park"
# Query an explicit week from the Oxford dropdown
uv run oxford-weekly --week "30 Mar 2026"
# Match keywords across all wards and parishes
uv run oxford-weekly --keywords "photovoltaics, heat pump, ASHP, PV"
```

## Config file

The CLI only loads config values when you pass an explicit file with `--config`.

CLI flags still win over config values, so this works well for keeping your usual
ward, mode, email recipient, and fallback settings in one place.

If your config uses `email_to`, you will also need a `.env` file with
`RESEND_API_KEY`.

Example:

```toml
debug = true
ward = ["churchill", "hinksey park"]
status_mode = "validated"
distance_around_ward = "0.25 miles"
distance_around_parish = "0.4 km"
keywords = "photovoltaics, heat pump, ASHP, PV"
major = true
email_to = "example@gmail.com"
```

`distance_around_ward` and `distance_around_parish` are optional and default to
`0`. They accept distance values with units such as `"0.25 miles"` or
`"0.4 km"`.

Examples with config:

```bash
# Load defaults from config and save HTML output locally
uv run oxford-weekly --config planning_update.toml --debug
# Load config but override status from the CLI
uv run oxford-weekly --config /path/to/planning_update.toml --status decided
```
