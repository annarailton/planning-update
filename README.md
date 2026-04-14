# Planning update

Basic tool that grabs a summary of latest Oxford planning applications of interest from the weekly list. 

https://public.oxford.gov.uk/online-applications/search.do?action=weeklyList

## Basic features 

- CLI that grabs applications by:
  - Date (defaults to latest week)
  - Ward
  - Parish
  - Keywords in the application description
  - Major applications
- Produces summary with descriptions and links
- Action that runs weekly and emails summary
- Config for preferences

## Current scraper

`main.py` fetches planning applications for the selected ward/parish filters
using the weekly list filters for either `Validated in this week` or `Decided in this week`.

The lookup data lives in [ward_mappings.json](/Users/annarailton/projects/planning-update/ward_mappings.json),
and [location_lookup.py](/Users/annarailton/projects/planning-update/location_lookup.py) loads it for the scraper.

By default it checks the latest week in the dropdown and falls back one week if there are
no results, which matches the current need to use `30 Mar 2026` when the most recent week
is empty. When that fallback happens, the CLI logs which week it is falling back from and to.

## Query flow

The scraper works in three stages:

1. Build the weekly-list search payload.
   `PlanningQuery` in [models.py](/Users/annarailton/projects/planning-update/models.py) resolves the optional human-readable ward and parish names to Oxford's internal codes and serializes the form payload for the selected week and mode (`validated` or `decided`).

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

Example:

```bash
uv run oxford-weekly
uv run oxford-weekly --debug
uv run oxford-weekly --parish "Littlemore"
uv run oxford-weekly --ward "churchill"
uv run oxford-weekly --week "30 Mar 2026"

python main.py
python main.py --parish "Littlemore"
python main.py --ward "churchill"
python main.py --ward "churchill" --parish "Littlemore"
python main.py --week "30 Mar 2026"
python main.py --decided
python main.py --strict
```

## Config file

The CLI can load default option values from `planning_update.toml` in the current
working directory, or from an explicit path passed with `--config`.

CLI flags still win over config values, so this works well for keeping your usual
ward, mode, email recipient, and fallback settings in one place.

Example:

```toml
debug = true
ward = "churchill"
parish = "Littlemore"
status_mode = "validated"
fallback_weeks = 1
strict = false
email_to = "example@gmail.com"
```

You can also nest the same values under `[cli]` if you prefer:

```toml
[cli]
ward = "churchill"
status_mode = "decided"
```

Examples with config:

```bash
uv run oxford-weekly --debug --output latest.html
uv run oxford-weekly --config /path/to/planning_update.toml --decided
python main.py --config planning_update.toml --no-strict
```
