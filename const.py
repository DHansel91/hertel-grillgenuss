"""Constants for the Hertel Grillgenuss integration."""

DOMAIN = "hertel_grillgenuss"

# Config entry keys
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_ZIPCODE = "zipcode"
CONF_SCAN_INTERVAL = "scan_interval"

# Defaults
DEFAULT_SCAN_INTERVAL = 60  # minutes
DEFAULT_SEARCH_OPT = "All"

# API
BASE_URL = "https://hertel-grillgenuss.de/standortsuche"

# Data keys returned / parsed
ATTR_LOCATIONS = "locations"
ATTR_LOCATION_NAME = "name"
ATTR_LOCATION_ADDRESS = "address"
ATTR_LOCATION_ZIPCODE = "zipcode"
ATTR_LOCATION_CITY = "city"
ATTR_LOCATION_DAY = "day"
ATTR_LOCATION_TIME = "time"
ATTR_LOCATION_DISTANCE = "distance"
ATTR_LOCATION_LAT = "latitude"
ATTR_LOCATION_LON = "longitude"
ATTR_LOCATION_INFO = "info"
