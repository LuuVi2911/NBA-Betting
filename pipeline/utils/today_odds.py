from sbrscrape import Scoreboard

def get_sbr_odds(sport='NBA', sportsbook='fanduel'):
    sb = Scoreboard(sport=sport)
    games = sb.games if hasattr(sb, 'games') else []
    dict_res = {}
    for game in games:
        home_team = game['home_team']
        away_team = game['away_team']
        money_line_home = game['home_ml'].get(sportsbook)
        money_line_away = game['away_ml'].get(sportsbook)
        totals = game['total'].get(sportsbook)
        dict_res[f"{home_team}:{away_team}"] = {
            'under_over_odds': totals,
            home_team: {'money_line_odds': money_line_home},
            away_team: {'money_line_odds': money_line_away}
        }
    return dict_res