"""Shared constants for the Oxford planning notifier."""

from pathlib import Path

# Ward, parish, and postcode data locations
WARD_DATA_PATH = Path(__file__).with_name("lookup") / "ward_mappings.json"
BOUNDARIES_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "boundaries"
    / "oxford_city_wards.geojson"
)
PARISH_BOUNDARIES_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "boundaries"
    / "oxford_city_parishes.geojson"
)
CODEPOINT_CSV_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "code_point_postcodes" / "ox.csv"
)
FUZZY_MATCH_THRESHOLD = 85

# Planning website stuff
BASE_URL = "https://public.oxford.gov.uk"
WEEKLY_LIST_URL = (
    "https://public.oxford.gov.uk/online-applications/search.do?action=weeklyList"
)
RESULTS_URL = "https://public.oxford.gov.uk/online-applications/weeklyListResults.do?action=firstPage"
MAJOR_APPLICATIONS_URL = (
    "https://www.oxford.gov.uk/planning-applications/current-planning-applications"
)
COMMITTEE_BASE_URL = "https://mycouncil.oxford.gov.uk"
PLANNING_COMMITTEE_MEETINGS_URL = (
    "https://mycouncil.oxford.gov.uk/ieListMeetings.aspx?CId=568&Year=0"
)
PLANNING_REVIEW_COMMITTEE_MEETINGS_URL = (
    "https://mycouncil.oxford.gov.uk/ieListMeetings.aspx?CId=147&Year=0"
)
DEFAULT_TIMEOUT_SECONDS = 30
RETRY_MAX_RETRIES = 4
RETRY_INITIAL_BACKOFF_SECONDS = 2.0
RATE_LIMIT_INITIAL_BACKOFF_SECONDS = 4.0
RATE_LIMIT_STATUS_CODES = {429}
RETRY_STATUS_CODES = {500, 502, 503, 504}
ENRICHMENT_REQUEST_DELAY_SECONDS = 0.5

# Cache
SCRAPER_CACHE_DIR = Path(".cache/planning-update")
APPLICATION_DETAILS_DECISION_TTL_SECONDS = 7 * 24 * 60 * 60  # stale cache after 7 days
MAJOR_APPLICATIONS_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60  # stale cache after 30 days

# Email stuff
RESEND_EMAILS_URL = "https://api.resend.com/emails"
DEFAULT_SENDER_ADDRESS = "planning@updates.railton.dev"

# Colours for the HTML output, based on the Tailwind CSS palette with some custom additions.
PAGE_BACKGROUND_COLOR = "#f5f1e8"
TEXT_PRIMARY_COLOR = "#1f2933"
TEXT_SECONDARY_COLOR = "#52606d"
TEXT_TERTIARY_COLOR = "#7b8794"
TEXT_STRONG_COLOR = "#364152"
SURFACE_PRIMARY_COLOR = "#ffffff"
SURFACE_SECONDARY_COLOR = "#f8fafc"
BORDER_SUBTLE_COLOR = "#d9e2ec"
ACCENT_WARM_COLOR = "#9f580a"
LINK_COLOR = "#0b6e4f"
SHADOW_COLOR = "rgba(15,23,42,0.06)"

# Colours associated with application status values, for consistent rendering in the HTML output.
SUCCESS_COLOR = "#18794e"
WARNING_COLOR = "#b26b00"
DANGER_COLOR = "#c81e1e"
