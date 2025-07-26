from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError, NotFound
import baseballquery
import numpy as np
from rest_api.models import SavedQuery
from rest_api.cache import QueryCache
from django.core.exceptions import ValidationError as DjangoValidationError
from copy import deepcopy

filter_params = ["filter_opposing", "filter_innings", "filter_top", "filter_stats", "filter_values", "filter_operators"]

nullable_cols = ["year", "player_id", "team", "month", "day", "game_id", "start_year", "end_year", "win", "loss"]

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
    "filter_home",
    "filter_opposing",
]

list_params_type_func = {
    "days_of_week": str,
    "pitching_team": str,
    "batting_team": str,
    "innings": int,
    "outs": int,
    "count": str,
    "strikes": int,
    "balls": int,
    "score_diff": int,
    "home_score": int,
    "away_score": int,
    "base_situation": int,
    "batter_lineup_pos": int,
    "player_field_position": int,
    "filter_innings": int,
    "filter_top": str,
    "filter_stats": str,
    "filter_values": int,
    "filter_operators": str,
}

bool_params = [
    "batter_home",
    "pitcher_home",
    "batter_starter",
    "pitcher_starter",
    "filter_opposing"
]

valid_filter_cols = [
    "AB_FL",
    "H_CD",
    "SH_FL",
    "SF_FL",
    "EVENT_OUTS_CT",
    "DP_FL",
    "TP_FL",
    "RBI_CT",
    "WP_FL",
    "PB_FL",
    "BATTEDBALL_CD",
    "BAT_DEST_ID",
    "RUN1_DEST_ID",
    "RUN2_DEST_ID",
    "RUN3_DEST_ID",
    "RUN1_SB_FL",
    "RUN2_SB_FL",
    "RUN3_SB_FL",
    "RUN1_CS_FL",
    "RUN2_CS_FL",
    "RUN3_CS_FL",
    "RUN1_PK_FL",
    "RUN2_PK_FL",
    "RUN3_PK_FL",
    "RUN1_RESP_PIT_ID",
    "RUN2_RESP_PIT_ID",
    "RUN3_RESP_PIT_ID",
    "HOME_TEAM_ID",
    "BAT_TEAM_ID",
    "FLD_TEAM_ID",
    "PA_TRUNC_FL",
    "START_BASES_CD",
    "END_BASES_CD",
    "RESP_BAT_START_FL",
    "RESP_PIT_START_FL",
    "PA_BALL_CT",
    "PA_OTHER_BALL_CT",
    "PA_STRIKE_CT",
    "PA_OTHER_STRIKE_CT",
    "EVENT_RUNS_CT",
    "BAT_SAFE_ERR_FL",
    "FATE_RUNS_CT",
    "MLB_STATSAPI_APPROX",
    "mlbam_id",
    "0-0",
    "0-1",
    "0-2",
    "1-0",
    "1-1",
    "1-2",
    "2-0",
    "2-1",
    "2-2",
    "3-0",
    "3-1",
    "3-2",
    "PA",
    "AB",
    "SH",
    "SF",
    "R",
    "RBI",
    "SB",
    "CS",
    "K",
    "BK",
    "UBB",
    "IBB",
    "HBP",
    "FC",
    "1B",
    "2B",
    "3B",
    "HR",
    "H",
    "DP",
    "TP",
    "ROE",
    "WP",
    "P",
    "GB",
    "FB",
    "LD",
    "PU",
    "ER",
    "T_UER",
    "UER",

    # Not actual columns, but the API allows filtering by these through backend logic
    "SCORE",
    "SCORE_DIFF",
]

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
        "count": "set_count",
        "strikes": "set_strikes_end",
        "balls": "set_balls_end",
        "score_diff": "set_score_diff",
        "home_score": "set_home_score",
        "away_score": "set_away_score",
        "base_situation": "set_base_situation",
    }
    for param, method_name in method_map.items():
        if param in params:
            getattr(splits, method_name)(params[param])

    if "filter_stats" in params:
        # Turn all the lists in params[filter_params] into list of dicts
        stat_filters_list = []
        for i in range(len(params["filter_stats"])):
            stat_filters_list.append({
                "inning": params["filter_innings"][i],
                "top": params["filter_top"][i],
                "stat": params["filter_stats"][i],
                "value": params["filter_values"][i],
                "operator": params["filter_operators"][i],
            })
        splits.filter_stats_by_innings(params["filter_home"], stat_filters_list, params["filter_opposing"])

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

    if "split" in query_params and query_params["split"] not in ["year", "career", "month", "game"]:
        raise ValidationError("split must be either 'year', 'career', 'month', or 'game'")

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

    if "batter_lineup_pos" in query_params:
        batter_lineup_pos = query_params["batter_lineup_pos"].split(",")
        if not all(pos.isdigit() and 1 <= int(pos) <= 9 for pos in batter_lineup_pos):
            raise ValidationError("batter_lineup_pos must be a comma-separated list of integers from 1 to 9")

    if "player_field_position" in query_params:
        player_field_position = query_params["player_field_position"].split(",")
        if not all(pos.isdigit() and 1 <= int(pos) <= 12 for pos in player_field_position):
            raise ValidationError("player_field_position must be a comma-separated list of integers from 1 to 12")

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

    if "count" in query_params:
        counts = query_params["count"].split(",")
        if not all(len(count) == 3 and count[0].isdigit() and count[1] == '-' and count[2].isdigit() for count in counts):
            raise ValidationError("count must be a comma-separated list of strings in the format 'strikes-balls' (e.g., '2-1')")
        if not all(0 <= int(count.split('-')[0]) <= 2 and 0 <= int(count.split('-')[1]) <= 3 for count in counts):
            raise ValidationError("strikes must be between 0 and 2, and balls must be between 0 and 3 in the count format 'strikes-balls' (e.g., '2-1')")

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

    if any(x in query_params for x in filter_params) and not all(x in query_params for x in filter_params):
        raise ValidationError("The filter feature requires all of filter_opposing, filter_innings, filter_top, filter_stats, filter_values, and filter_operators to be specified")

    if "filter_home" in query_params and query_params["filter_home"] not in ["home", "away", "either"]:
        raise ValidationError("filter_home must be 'home', 'away', or 'either'")

    if "filter_opposing" in query_params and query_params["filter_opposing"] not in ["Y", "N"]:
        raise ValidationError("filter_opposing must be 'Y' or 'N'")

    if "filter_innings" in query_params:
        innings = query_params["filter_innings"].split(",")
        try:
            innings = [int(i) for i in innings]
            if not all(1 <= i for i in innings):
                raise ValidationError("filter_innings must be a comma-separated list of integers greater than or equal to 1")
        except ValueError:
            raise ValidationError("filter_innings must be a comma-separated list of integers")

    if "filter_top" in query_params:
        top = query_params["filter_top"].split(",")
        if not all(t in ["Y", "N"] for t in top):
            raise ValidationError("filter_top must be a comma-separated list of 'Y' or 'N' values")

    if "filter_stats" in query_params:
        cols = query_params["filter_stats"].split(",")
        if not all(col in valid_filter_cols for col in cols):
            raise ValidationError(f"filter_stats must be a comma-separated list of valid columns: {', '.join(valid_filter_cols)}")

    if "filter_values" in query_params:
        values = query_params["filter_values"].split(",")
        try:
            values = [int(value) for value in values]
        except ValueError:
            raise ValidationError("filter_values must be a comma-separated list of integers")

    if "filter_operators" in query_params:
        operators = query_params["filter_operators"].split(",")
        valid_operators = ["=", "<", ">", "<=", ">=", "!="]
        if not all(op in valid_operators for op in operators):
            raise ValidationError(f"filter_operators must be a comma-separated list of valid operators: {', '.join(valid_operators)}")


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

        # Process boolean params
        for key in bool_params:
            if key in params:
                if params[key] in ["Y", "N"]:
                    params[key] = True if params[key] == "Y" else False

        # Process filter_top boolean values
        if "filter_top" in params:
            params["filter_top"] = [True if val == "Y" else False for val in params["filter_top"]]

            # Make sure all filter_params lists are the same length
            for param in filter_params:
                if param in params and (param != "filter_opposing" and len(params[param]) != len(params["filter_top"])):
                    raise ValidationError(f"All filter parameters must have the same number of elements. '{param}' has {len(params[param])} elements, but 'filter_top' has {len(params['filter_top'])} elements.")

        # Initialize cache and search for data
        cache = QueryCache()
        stats, years_found = cache.get_data(params)
        if len(years_found) == 0:   # If no data matching this query is found in the cache, fully calculate it then add it to the cache
            s = baseballquery.BattingStatSplits(start_year=params["start_year"], end_year=params["end_year"])
            proc_params(params, s)
            s.calculate_stats()
            s.stats.replace([np.inf, -np.inf], np.nan, inplace=True)
            s.stats.reset_index(inplace=True, drop=False)
            for col in nullable_cols:
                s.stats[col] = s.stats[col].fillna("N/A")
            s.stats = s.stats.fillna("NaN")
            cache.put_data(params, s.stats, years_found)
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
                for col in nullable_cols:
                    s.stats[col] = s.stats[col].fillna("N/A")
                s.stats = s.stats.fillna("NaN")
                stats.extend(s.stats.to_dict(orient='records', index=True))
                cache.put_data(params, s.stats, years_found)
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

        # Process boolean params
        for key in bool_params:
            if key in params:
                if params[key] in ["Y", "N"]:
                    params[key] = True if params[key] == "Y" else False

        if "filter_top" in params:
            params["filter_top"] = [True if val == "Y" else False for val in params["filter_top"]]

            # Make sure all filter_params lists are the same length
            for param in filter_params:
                if param in params and (param != "filter_opposing" and len(params[param]) != len(params["filter_top"])):
                    raise ValidationError(f"All filter parameters must have the same number of elements. '{param}' has {len(params[param])} elements, but 'filter_top' has {len(params['filter_top'])} elements.")

        stats, years_found = cache.get_data(params)
        if len(years_found) == 0:
            s = baseballquery.PitchingStatSplits(start_year=params["start_year"], end_year=params["end_year"])
            proc_params(params, s)
            s.calculate_stats()
            s.stats.replace([np.inf, -np.inf], np.nan, inplace=True)
            s.stats.reset_index(inplace=True, drop=False)
            for col in nullable_cols:
                s.stats[col] = s.stats[col].fillna("N/A")
            s.stats = s.stats.fillna("NaN")
            cache.put_data(params, s.stats, years_found)
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
                for col in nullable_cols:
                    s.stats[col] = s.stats[col].fillna("N/A")
                s.stats = s.stats.fillna("NaN")
                stats.extend(s.stats.to_dict(orient='records', index=True))
                cache.put_data(params, s.stats, years_found)
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

class SavedQueries(APIView):
    def get(self, request):
        uuid = request.query_params.get("uuid")
        try:
            saved_query = SavedQuery.objects.get(key=uuid)
        except SavedQuery.DoesNotExist:
            raise NotFound("Saved query not found.")
        except DjangoValidationError:
            raise ValidationError("Invalid UUID format.")
        return Response(saved_query.to_dict())

    def post(self, request):
        params = request.data.get("params")
        if not params:
            raise ValidationError("'params' is required.")
        if not isinstance(params, dict):
            raise ValidationError("'params' must be a dictionary.")

        if "type" not in params:
            raise ValidationError("'type' must be specified in params.")
        if params["type"] not in ["batting", "pitching"]:
            raise ValidationError("'type' in params must be either 'batting' or 'pitching'.")
        # Convert lists to comma separated lists for validation
        params_new = deepcopy(params)
        to_delete = []
        for key, value in params_new.items():
            if isinstance(value, list):
                if len(value) == 0:
                    to_delete.append(key)
                else:
                    params_new[key] = ",".join(map(str, value))
            if value is None or value == "":
                to_delete.append(key)
            if isinstance(value, bool):
                params_new[key] = "Y" if value else "N"
        for key in to_delete:
            del params_new[key]
        param_validation(params_new)
        
        
        saved_query = SavedQuery(params=params)
        saved_query.save()
        return Response({"message": "Saved query created successfully.", "uuid": str(saved_query.key)}, status=201)
