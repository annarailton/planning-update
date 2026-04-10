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
