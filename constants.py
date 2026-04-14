"""Shared constants for the Oxford planning notifier."""

from pathlib import Path

# Config locations
DEFAULT_CONFIG_FILENAME = "planning_update.toml"

# Ward and parish data locations
WARD_DATA_PATH = Path(__file__).with_name("ward_mappings.json")
FUZZY_MATCH_THRESHOLD = 85

# Planning website stuff
BASE_URL = "https://public.oxford.gov.uk"
WEEKLY_LIST_URL = (
    "https://public.oxford.gov.uk/online-applications/search.do?action=weeklyList"
)
RESULTS_URL = "https://public.oxford.gov.uk/online-applications/weeklyListResults.do?action=firstPage"
DEFAULT_TIMEOUT_SECONDS = 30

# Email stuff
RESEND_EMAILS_URL = "https://api.resend.com/emails"
DEFAULT_SENDER_ADDRESS = "anna@updates.railton.dev"

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
