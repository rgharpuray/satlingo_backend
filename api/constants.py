"""
Visual Enhancement Constants

Location: api/constants.py
Summary: Defines color palettes and default icon URLs for Duolingo-style visual icons.
Usage: Imported by models.py for validators and serializers.py for effective_* computed properties.
"""

# GCS bucket prefix for icon URLs (used in validation)
GCS_ICON_URL_PREFIX = 'https://storage.googleapis.com/keuvi-app/icons/'

# Duolingo-inspired color palette for icons
ICON_COLOR_CHOICES = [
    ('#58CC02', 'Green - Primary'),       # Main Duolingo green
    ('#1CB0F6', 'Blue - Skills'),         # Skill icons
    ('#FF9600', 'Orange - Practice'),     # Practice/review
    ('#FF4B4B', 'Red - Challenge'),       # Hard/challenge
    ('#CE82FF', 'Purple - Special'),      # Premium/special
    ('#FFD900', 'Yellow - Achievement'),  # Achievements/XP
]

# Default fallback color when no category-specific default exists
DEFAULT_FALLBACK_COLOR = '#58CC02'

# Default colors by category
DEFAULT_COLORS = {
    'reading': '#1CB0F6',   # Blue
    'writing': '#CE82FF',   # Purple
    'math': '#FF9600',      # Orange
}

# Default icon URLs by category
# Set to None until real assets are uploaded to GCS
DEFAULT_ICONS = {
    'reading': None,
    'writing': None,
    'math': None,
}
