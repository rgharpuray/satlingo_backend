"""
Visual Enhancement Constants

Location: api/constants.py
Summary: Defines color palettes and default icon URLs for Duolingo-style visual icons.
Usage: Imported by models.py for validators and serializers.py for effective_* computed properties.
"""

# Duolingo-inspired color palette for icons
ICON_COLOR_CHOICES = [
    ('#58CC02', 'Green - Primary'),       # Main Duolingo green
    ('#1CB0F6', 'Blue - Skills'),         # Skill icons
    ('#FF9600', 'Orange - Practice'),     # Practice/review
    ('#FF4B4B', 'Red - Challenge'),       # Hard/challenge
    ('#CE82FF', 'Purple - Special'),      # Premium/special
    ('#FFD900', 'Yellow - Achievement'),  # Achievements/XP
]

# Default colors by category
DEFAULT_COLORS = {
    'reading': '#1CB0F6',   # Blue
    'writing': '#CE82FF',   # Purple
    'math': '#FF9600',      # Orange
}

# Default icon URLs by category
# Placeholder URLs - will be updated when assets are created
DEFAULT_ICONS = {
    'reading': 'https://storage.googleapis.com/keuvi-app/icons/defaults/reading.webp',
    'writing': 'https://storage.googleapis.com/keuvi-app/icons/defaults/writing.webp',
    'math': 'https://storage.googleapis.com/keuvi-app/icons/defaults/math.webp',
}
