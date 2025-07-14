from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
import baseballquery
import numpy as np
from rest_api.cache import QueryCache

split_params = [
    # "start_year",
    # "end_year",
    # "split",
    # "find",
    # "days_of_week",
    "batter_handedness_pa",
    "pitcher_handedness",
    "batter_starter",
    "pitcher_starter",
    "batter_lineup_pos",
    "player_field_position",
    "batter_home",
    "pitcher_home",
    # "pitching_team",
    # "batting_team",
    # "innings",
    # "outs",
    # "strikes",
    # "balls",
    # "score_diff",
    # "home_score",
    # "away_score",
    # "base_situation",
]

list_params_type_func = {
    "days_of_week": str,
    "pitching_team": str,
    "batting_team": str,
    "innings": int,
    "outs": int,
    "strikes": int,
    "balls": int,
    "score_diff": int,
    "home_score": int,
    "away_score": int,
    "base_situation": int,
}

def proc_params(params, splits: baseballquery.stat_splits.StatSplits):
    method_map = {
        "split": "set_split",
        "find": "set_subdivision",
        "days_of_week": "set_days_of_week",
        "batter_handedness_pa": "set_batter_handedness_pa",
        "pitcher_handedness": "set_pitcher_handedness",
        "batter_starter": "set_batter_starter",
        "pitcher_starter": "set_pitcher_starter",
        "batter_lineup_pos": "set_batter_lineup_pos",
        "player_field_position": "set_player_field_position",
        "batter_home": "set_batter_home",
        "pitcher_home": "set_pitcher_home",
        "pitching_team": "set_pitching_team",
        "batting_team": "set_batting_team",
        "innings": "set_innings",
        "outs": "set_outs",
        "strikes": "set_strikes",
        "balls": "set_balls",
        "score_diff": "set_score_diff",
        "home_score": "set_home_score",
        "away_score": "set_away_score",
        "base_situation": "set_base_situation",
    }
    for param, method_name in method_map.items():
        if param in params:
            getattr(splits, method_name)(params[param])

def param_validation(query_params):
    if "start_year" in query_params and "end_year" in query_params:
        try:
            start_year = int(query_params["start_year"])
            end_year = int(query_params["end_year"])
        except ValueError:
            raise ValidationError("start_year and end_year must be integers")
        if start_year > end_year:
            raise ValidationError("start_year cannot be greater than end_year")
    elif "start_year" in query_params and "end_year" not in query_params:
        raise ValidationError("end_year must be provided if start_year is provided")
    elif "end_year" in query_params and "start_year" not in query_params:
        raise ValidationError("start_year must be provided if end_year is provided")

    if "split" in query_params and query_params["split"] not in ["year", "career"]:
        raise ValidationError("split must be either 'year' or 'career'")

    if "find" in query_params and query_params["find"] not in ["player", "team"]:
        raise ValidationError("find must be either 'player' or 'team'")

    if "days_of_week" in query_params:
        days_of_week = query_params["days_of_week"].split(",")
        valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
        if not all(day in valid_days for day in days_of_week):
            raise ValidationError(f"days_of_week must be one or more of {', '.join(valid_days)}")

    if "batter_handedness_pa" in query_params and query_params["batter_handedness_pa"] not in ["L", "R"]:
        raise ValidationError("batter_handedness_pa must be 'L', or 'R'")

    if "pitcher_handedness" in query_params and query_params["pitcher_handedness"] not in ["L", "R"]:
        raise ValidationError("pitcher_handedness must be 'L', or 'R'")

    if "batter_starter" in query_params and query_params["batter_starter"] not in ["Y", "N"]:
        raise ValidationError("batter_starter must be 'Y' or 'N'")

    if "pitcher_starter" in query_params and query_params["pitcher_starter"] not in ["Y", "N"]:
        raise ValidationError("pitcher_starter must be 'Y' or 'N'")

    if "batter_lineup_pos" in query_params and query_params["batter_lineup_pos"] not in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        raise ValidationError("batter_lineup_pos must be an integer from 1 to 9")

    if "player_field_position" in query_params and query_params["player_field_position"] not in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]:
        raise ValidationError("player_field_position must be an integer from 1 to 12")

    if "batter_home" in query_params and query_params["batter_home"] not in ["Y", "N"]:
        raise ValidationError("batter_home must be 'Y' or 'N'")

    if "pitcher_home" in query_params and query_params["pitcher_home"] not in ["Y", "N"]:
        raise ValidationError("pitcher_home must be 'Y' or 'N'")

    if "pitching_team" in query_params:
        teams = query_params["pitching_team"].split(",")
        if not all(team.isupper() and team.isalpha() and len(team) == 3 for team in teams):
            raise ValidationError("pitching_team must be a comma-separated list of 3-letter uppercase team codes")

    if "batting_team" in query_params:
        teams = query_params["batting_team"].split(",")
        if not all(team.isupper() and team.isalpha() and len(team) == 3 for team in teams):
            raise ValidationError("batting_team must be a comma-separated list of 3-letter uppercase team codes")

    if "innings" in query_params:
        innings = query_params["innings"].split(",")
        try:
            innings = [int(i) for i in innings]
            if not all(1 <= i for i in innings):
                raise ValidationError("innings must be a comma-separated list of integers greater than or equal to 1")
        except ValueError:
            raise ValidationError("innings must be a comma-separated list of integers")

    if "outs" in query_params:
        outs = query_params["outs"].split(",")
        try:
            outs = [int(o) for o in outs]
            if not all(0 <= o < 3 for o in outs):
                raise ValidationError("outs must be a comma-separated list of integers from 0 to 2")
        except ValueError:
            raise ValidationError("outs must be a comma-separated list of integers")

    if "strikes" in query_params:
        strikes = query_params["strikes"].split(",")
        try:
            strikes = [int(s) for s in strikes]
            if not all(0 <= s <= 3 for s in strikes):
                raise ValidationError("strikes must be a comma-separated list of integers from 0 to 3")
        except ValueError:
            raise ValidationError("strikes must be a comma-separated list of integers")

    if "balls" in query_params:
        balls = query_params["balls"].split(",")
        try:
            balls = [int(b) for b in balls]
            if not all(0 <= b <= 4 for b in balls):
                raise ValidationError("balls must be a comma-separated list of integers from 0 to 4")
        except ValueError:
            raise ValidationError("balls must be a comma-separated list of integers")

    if "score_diff" in query_params:
        score_diff = query_params["score_diff"].split(",")
        try:
            score_diff = [int(sd) for sd in score_diff]
        except ValueError:
            raise ValidationError("score_diff must be a comma-separated list of integers")

    if "home_score" in query_params:
        home_score = query_params["home_score"].split(",")
        try:
            home_score = [int(hs) for hs in home_score]
            if not all(hs >= 0 for hs in home_score):
                raise ValidationError("home_score must be a comma-separated list of non-negative integers")
        except ValueError:
            raise ValidationError("home_score must be a comma-separated list of integers")

    if "away_score" in query_params:
        away_score = query_params["away_score"].split(",")
        try:
            away_score = [int(as_) for as_ in away_score]
            if not all(as_ >= 0 for as_ in away_score):
                raise ValidationError("away_score must be a comma-separated list of non-negative integers")
        except ValueError:
            raise ValidationError("away_score must be a comma-separated list of integers")

    if "base_situation" in query_params:
        base_situation = query_params["base_situation"].split(",")
        try:
            base_situation = [int(bs) for bs in base_situation]
            if not all(0 <= bs <= 7 for bs in base_situation):
                raise ValidationError("base_situation must be a comma-separated list of integers from 0 to 7")
        except ValueError:
            raise ValidationError("base_situation must be a comma-separated list of integers")


class BattingStatQuery(APIView):
    def get(self, request):
        param_validation(request.query_params)
        params = {
            "type": "batting",
            "start_year": int(request.query_params.get("start_year", 2025)),
            "end_year": int(request.query_params.get("end_year", 2025)),
            "split": request.query_params.get("split", "year"),
            "find": request.query_params.get("find", "player"),
            **{k: v for k, v in request.query_params.items() if k in split_params},
            **{k: [list_params_type_func[k](elem) for elem in val.split(",")] for k, val in request.query_params.items() if k in list_params_type_func}
        }

        for key, value in params.items():
            if type(value) is list:
                params[key] = sorted(value)

        # Initialize cache and search for data
        cache = QueryCache()
        stats, years_found = cache.get_data(params)
        if len(years_found) == 0:   # If no data matching this query is found in the cache, fully calculate it then add it to the cache
            s = baseballquery.BattingStatSplits(start_year=params["start_year"], end_year=params["end_year"])
            proc_params(params, s)
            s.calculate_stats()
            s.stats.replace([np.inf, -np.inf], np.nan, inplace=True)
            s.stats.reset_index(inplace=True, drop=False)
            for col in ["year", "player_id", "team", "month", "day", "game_id", "start_year", "end_year"]:
                s.stats[col] = s.stats[col].fillna("N/A")
            s.stats = s.stats.fillna("NaN")
            cache.put_data(params, s.stats)
            stats = s.stats.to_dict(orient='records', index=True)
        else:
            # Otherwise, see what years are missing for this query and calculate those
            all_years = set(range(params["start_year"], params["end_year"] + 1))
            if years_found != all_years:
                missing_years = all_years - years_found
                years_list = list(missing_years)
                s = baseballquery.BattingStatSplits(years_list=years_list)
                proc_params(params, s)
                s.calculate_stats()
                s.stats.replace([np.inf, -np.inf], np.nan, inplace=True)
                s.stats.reset_index(inplace=True, drop=False)
                for col in ["year", "player_id", "team", "month", "day", "game_id", "start_year", "end_year"]:
                    s.stats[col] = s.stats[col].fillna("N/A")
                s.stats = s.stats.fillna("NaN")
                stats.extend(s.stats.to_dict(orient='records', index=True))
                cache.put_data(params, s.stats)
        cache.close()

        # Filter and sort the stats based on query parameters
        if len(stats) != 0:
            min_pa = request.query_params.get("min_pa", 0)
            stats = list(filter(lambda x: x["PA"] >= int(min_pa), stats))
            sort = request.query_params.get("sort", "year,player_id")
            fields = sort.split(",")
            if fields:
                for field in reversed(fields):
                    if field.lstrip("-") not in stats[0]:
                        raise ValueError(f"Field '{field}' not found in stats")
                    # Sort the stats based on the fields
                    negative = field.startswith("-")
                    field = field.lstrip("-")
                    field_is_numeric = field not in ["player_id", "team", "game_id"]
                    stats.sort(key=lambda x: x[field] if (type(x[field]) in (int, float) and field_is_numeric) or not field_is_numeric else (float("-inf") if negative else float("inf")), reverse=negative)

        paginator = PageNumberPagination()
        paginator.page_size = request.query_params.get("page_size", 50)
        page = paginator.paginate_queryset(stats, request, view=self)
        return paginator.get_paginated_response(page)


class PitchingStatQuery(APIView):
    def get(self, request):
        param_validation(request.query_params)
        cache = QueryCache()
        params = {
            "type": "pitching",
            "start_year": int(request.query_params.get("start_year", 2025)),
            "end_year": int(request.query_params.get("end_year", 2025)),
            "split": request.query_params.get("split", "year"),
            "find": request.query_params.get("find", "player"),
            **{k: v for k, v in request.query_params.items() if k in split_params},
            **{k: [list_params_type_func[k](elem) for elem in val.split(",")] for k, val in request.query_params.items() if k in list_params_type_func}
        }

        for key, value in params.items():
            if type(value) is list:
                params[key] = sorted(value)
        stats, years_found = cache.get_data(params)
        if len(years_found) == 0:
            s = baseballquery.PitchingStatSplits(start_year=params["start_year"], end_year=params["end_year"])
            proc_params(params, s)
            s.calculate_stats()
            s.stats.replace([np.inf, -np.inf], np.nan, inplace=True)
            s.stats.reset_index(inplace=True, drop=False)
            for col in ["year", "player_id", "team", "month", "day", "game_id", "start_year", "end_year"]:
                s.stats[col] = s.stats[col].fillna("N/A")
            s.stats = s.stats.fillna("NaN")
            cache.put_data(params, s.stats)
            stats = s.stats.to_dict(orient='records', index=True)
        else:
            all_years = set(range(params["start_year"], params["end_year"] + 1))
            if years_found != all_years:
                missing_years = all_years - years_found
                years_list = list(missing_years)
                s = baseballquery.PitchingStatSplits(years_list=years_list)
                proc_params(params, s)
                s.calculate_stats()
                s.stats.replace([np.inf, -np.inf], np.nan, inplace=True)
                s.stats.reset_index(inplace=True, drop=False)
                for col in ["year", "player_id", "team", "month", "day", "game_id", "start_year", "end_year"]:
                    s.stats[col] = s.stats[col].fillna("N/A")
                s.stats = s.stats.fillna("NaN")
                stats.extend(s.stats.to_dict(orient='records', index=True))
                cache.put_data(params, s.stats)
        cache.close()

        if len(stats) != 0:
            min_ip = request.query_params.get("min_ip", 0)
            stats = list(filter(lambda x: x["IP"] >= int(min_ip), stats))
            sort = request.query_params.get("sort", "year,player_id")
            fields = sort.split(",")
            if fields:
                for field in reversed(fields):
                    if field.lstrip("-") not in stats[0]:
                        raise ValueError(f"Field '{field}' not found in stats")
                    # Sort the stats based on the fields
                    negative = field.startswith("-")
                    field = field.lstrip("-")
                    field_is_numeric = field not in ["player_id", "team", "game_id"]
                    stats.sort(key=lambda x: x[field] if (type(x[field]) in (int, float) and field_is_numeric) or not field_is_numeric else (float("-inf") if negative else float("inf")), reverse=negative)

        paginator = PageNumberPagination()
        paginator.page_size = request.query_params.get("page_size", 50)
        page = paginator.paginate_queryset(stats, request, view=self)
        return paginator.get_paginated_response(page)