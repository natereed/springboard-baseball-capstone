import argparse
import pandas as pd
import os

# Script generates player-by-player observations, which merges the salary data and aggregates all
# the performance data for that player, going back the specified number of years.
# TODO:
#  -Recalculate all averages. It would be easier to do this before generating the observations. Put it here
#   or in the generate_performance_db.py script.
#  -Create new features:
#   1. Years of experience, ie. number of years of player performance data
#   2. Number of wins per player (rollup team wins --- this might need to go in the performance data first,
#      before the team column is removed)

parser = argparse.ArgumentParser()
parser.add_argument("seasons", type=str)
parser.add_argument("num_prior_years", type=int)
parser.add_argument("--include_current_year", dest='include_current_year', action='store_true')
parser.add_argument("--exclude_current_year", dest='include_current_year', action='store_false')
args = parser.parse_args()

seasons = [int(season) for season in args.seasons.split(",")]
num_prior_years = args.num_prior_years

salaries_df = pd.read_csv(os.path.join("..", "data", "db", "Salaries.csv"))
salaries_df = salaries_df[salaries_df['Year'].isin(pd.Series(seasons))]
salaries_df.sort(columns=['Year', 'Player Id'], ascending=[0, 1])
performance_df = pd.read_csv(os.path.join("..", "data", "db", "Performance.csv"))

missing_players = []

stats = {}
print(str(len(salaries_df)) + " salaries.")
for index, salary_row in salaries_df.iterrows():
    player_id = salary_row['Player Id']  # short name, like 'bcolon'
    salary_year = salary_row['Year']
    print("Player {} in salary year {}".format(player_id, salary_year))
    #print("Player {} in salary year {}".format(player_id, salary_year))

    # Load performance data for player
    subset_ind = (performance_df['Player Id'] == player_id)
    if args.include_current_year:
        print("Including current year")
        subset_ind &= (performance_df['Year'] <= salary_year)
    else:
        print("Excluding current year!")
        subset_ind &= (performance_df['Year'] < salary_year)
    player_df = performance_df[subset_ind]
    print(str(len(player_df)) + " entries.")

    # Replace ind. years with aggregate years, if they exist

    # Iterate over performance stats for the given player
    # Each row is for a different year. Assemble all years into a single row.
    # Player Id, Year, Team, LG, Year.G, Year.AB,... Year-1.G, Year-1.AB, etc.
    if len(player_df) > 0:
        stats[player_id] = {'Salary Year': str(salary_year),
                            'Annual Salary': salary_row['Avg Annual']}

        # Now, subset to num_prior_years and spit out stats for each year
        for index, year_row in player_df[player_df['Year'] >= salary_year - num_prior_years].iterrows():
            play_year = year_row['Year']
            print("Stats for player {}, year {}".format(player_id, play_year))
            for column in performance_df.columns[3:].values:
                year_diff = salary_year - play_year
                if year_diff == 0:
                    years_relative = ""
                else:
                    years_relative = "-{}".format(year_diff)
                stat_name = "{}.Year{}".format(column, years_relative)
                stats[player_id][stat_name] = year_row[column]

        # Now, calcuate aggregate functions by player group (we don't need to group-by since we've
        # already subsetted on player id).
        # Note that these calculations exclude the current year, if the exclude_current_year flag is set
        stats[player_id]['Batting_Career_Max_AVG'] = player_df['Batting_AVG'].max()
        stats[player_id]['Batting_Career_Min_AVG'] = player_df['Batting_AVG'].min()
        if player_df['Batting_AB'].sum() > 0:
            stats[player_id]['Batting_Career_AVG'] = player_df['Batting_H'].sum() / player_df['Batting_AB'].sum()
        else:
            stats[player_id]['Batting_Career_AVG'] = 0.0

    else:
        print("No performance stats found.")
        missing_players.append({'Player Id' : player_id,
                                'Salary Year' : salary_year,
                                'Name' : salary_row['Name']})

import csv
with open("missing_performance.csv", "w") as missing_stats_out:
    writer = csv.DictWriter(missing_stats_out, ['Player Id', 'Salary Year', 'Name'])
    writer.writeheader()
    for missing_player in missing_players:
        writer.writerow(missing_player)

print(stats)

import json
with open("stats.json", "w") as stats_out:
    json.dump(stats, stats_out)

#print(stats)

print("Creating data frame...")
cols = []
for player_id in stats.keys():
    d = stats[player_id]
    cols.extend(list(d.keys()))
cols = list(set(cols))
cols.sort()
cols.insert(0, 'Player Id')
cols.remove('Annual Salary')
cols.remove('Salary Year')
cols.insert(1, 'Salary Year')
cols.insert(2, 'Annual Salary')

import csv
with open(os.path.join("..", "data", "db", "Observations.csv"), "w") as obs_out:
    writer = csv.DictWriter(obs_out, cols)
    writer.writeheader()
    for player_id in stats.keys():
        d = stats[player_id]
        d['Player Id'] = player_id
        writer.writerow(d)




