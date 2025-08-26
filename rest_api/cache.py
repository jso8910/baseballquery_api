import lmdb
import msgspec.json as json
from hashlib import sha1

class QueryCache:
    def __init__(self, db_path="lmdb_db", map_size=1024*1024*1024*1024):
        self.env = lmdb.open(db_path, map_size=map_size, readahead=False, max_dbs=3)
        self.calls = self.env.open_db(b"calls")
        self.years = self.env.open_db(b"years", dupsort=True)

    def get_data(self, params):
        if params["split"] != "career":
            # Split the params into multiple params_dicts with year: year_value for each year in [start_year, end_year]
            keys = []
            for year in range(params["start_year"], params["end_year"] + 1):
                params_dict = params.copy()
                del params_dict["start_year"]
                del params_dict["end_year"]
                params_dict["year"] = year
                h = sha1(json.encode(params_dict, order="deterministic")).digest()
                keys.append(h)
            data = []
            years_found = set()
            with self.env.begin(write=False) as txn:
                for key in keys:
                    h = key
                    stats = txn.get(h, db=self.calls)
                    if stats is not None:
                        data.extend(json.decode(stats))
                        year = int.from_bytes(txn.get(h, db=self.years))
                        years_found.add(year)

            return data, years_found
        else:
            # For career stats, just use the original params with start_year and end_year
            h = sha1(json.encode(params, order="deterministic")).digest()
            with self.env.begin(write=False) as txn:
                stats = txn.get(h, db=self.calls)
                if stats is not None:
                    return json.decode(stats), set(year for year in range(params["start_year"], params["end_year"] + 1))
                else:
                    return [], set()

    def put_data(self, params, stats, years_found):
        if params["split"] != "career":
            # Split the params into multiple params_dicts with year: year_value for each year in [start_year, end_year]
            for year in range(params["start_year"], params["end_year"] + 1):
                if year in years_found:
                    continue
                params_dict = params.copy()
                del params_dict["start_year"]
                del params_dict["end_year"]
                params_dict["year"] = year
                h = sha1(json.encode(params_dict, order="deterministic")).digest()
                stats_for_year = stats[stats['year'] == year].to_dict(orient='records', index=True)

                with self.env.begin(write=True) as txn:
                    txn.put(h, json.encode(stats_for_year), db=self.calls)
                    txn.put(h, year.to_bytes(2), db=self.years)
        else:
            # For career stats, just use the original params with start_year and end_year
            h = sha1(json.encode(params, order="deterministic")).digest()
            with self.env.begin(write=True) as txn:
                txn.put(h, json.encode(stats.to_dict(orient='records', index=True)), db=self.calls)
                for year in range(params["start_year"], params["end_year"] + 1):
                    txn.put(h, year.to_bytes(2), db=self.years)
    def close(self):
        self.env.close()

    def delete_year_data(self, year):
        with self.env.begin(write=True) as txn:
            for key, val in txn.cursor(db=self.calls):
                if int.from_bytes(txn.get(key, db=self.years)) == year:
                    txn.delete(key, db=self.calls)
                    txn.delete(key, db=self.years)