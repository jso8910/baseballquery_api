import baseballquery
import datetime
from rest_api.cache import QueryCache

data_current_year = baseballquery.utils.get_year_events(datetime.datetime.now().year)
# Update data and check if any new games from the current year were added
baseballquery.update_data()
data_current_year_new = baseballquery.utils.get_year_events(datetime.datetime.now().year)

# If any new rows were added
if data_current_year_new.shape[0] != data_current_year.shape[0]:
    # New games were added for the current year
    print("New games found for the current year, deleting cache for this year")
    cache = QueryCache()
    cache.delete_year_data(2025)