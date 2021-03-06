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
parser.add_argument("start_season", type=str)
parser.add_argument("num_prior_years", type=int)
parser.add_argument("--include_current_year", dest='include_current_year', action='store_true')
parser.add_argument("--exclude_current_year", dest='include_current_year', action='store_false')
args = parser.parse_args()

seasons = list(range(int(args.start_season), 2016))
num_prior_years = args.num_prior_years

allstar_df = pd.read_csv(os.path.join("..", "data", "lahman", "baseballdatabank-master", "core", "AllstarFull.csv"))
salaries_df = pd.read_csv(os.path.join("..", "data", "lahman", "baseballdatabank-master", "core", "Salaries.csv"))
salaries_df = salaries_df[salaries_df['yearID'].isin(pd.Series(seasons))]
salaries_df.sort(columns=['yearID', 'playerID'], ascending=[0, 1])

batting_post_season_df = pd.read_csv(os.path.join("..", "data", "lahman", "baseballdatabank-master", "core", "BattingPost.csv"))
pitching_post_season_df = pd.read_csv(os.path.join("..", "data", "lahman", "baseballdatabank-master", "core", "PitchingPost.csv"))
fielding_post_season_df = pd.read_csv(os.path.join("..", "data", "lahman", "baseballdatabank-master", "core", "FieldingPost.csv"))
performance_post_season_df = pd.merge(batting_post_season_df,
                                      pd.merge(pitching_post_season_df,
                                               fielding_post_season_df,
                                               on=['playerID','yearID','round','teamID']),
                                      on=['playerID', 'yearID', 'round', 'teamID'])
performance_df = pd.read_csv(os.path.join("..", "data", "db", "Performance.csv"))

# Rename columns
performance_df.rename(columns={'Player Id': 'playerID', 'Year' : 'yearID'}, inplace=True)
missing_players = []

observations = []
metastats = {}
metastats['num_salaries'] = len(salaries_df)
for season in seasons:
    metastats[season] = 0

for index, salary_row in salaries_df.iterrows():
    player_id = salary_row['playerID']  # short name, like 'bcolon'
    salary_year = salary_row['yearID']
    salary_team = salary_row['teamID']

    print("Player {} in salary year {}".format(player_id, salary_year))
    #print("Player {} in salary year {}".format(player_id, salary_year))

    # Load performance data for player
    subset_ind = (performance_df['playerID'] == player_id)
    if args.include_current_year:
        #print("Including current year")
        subset_ind &= (performance_df['yearID'] <= salary_year)
    else:
        #print("Excluding current year!")
        subset_ind &= (performance_df['yearID'] < salary_year)
    player_df = performance_df[subset_ind]
    print(str(len(player_df)) + " entries.")

    metastats[salary_year] += 1
    stats = {}
    stats = {'Salary Year': str(salary_year),
             'Annual Salary': salary_row['salary'],
             'Player Id': player_id,
             'Salary Team': salary_team}

    # Iterate over performance stats for the given player
    # Each row is for a different year. Assemble all years into a single row.
    # playerID, Year, Team, LG, Year.G, Year.AB,... Year-1.G, Year-1.AB, etc.
    if len(player_df) > 0:
        # Now, subset to num_prior_years and spit out stats for each year
        for index, year_row in player_df[player_df['yearID'] >= salary_year - num_prior_years].iterrows():
            play_year = year_row['yearID']
            #print("Stats for player {}, year {}".format(player_id, play_year))
            for column in performance_df.columns[3:].values:
                year_diff = salary_year - play_year
                if year_diff == 0:
                    years_relative = ""
                else:
                    years_relative = "-{}".format(year_diff)
                stat_name = "{}.Year{}".format(column, years_relative)
                stats[stat_name] = year_row[column]

        # Now, calcuate aggregate functions by player group (we don't need to group-by since we've
        # already subsetted on player id).
        # Note that these calculations exclude the current year, if the exclude_current_year flag is set

        # Batting Career stats
        stats['Batting_Career_Max_AVG'] = player_df['Batting_AVG'].max()
        stats['Batting_Career_Min_AVG'] = player_df['Batting_AVG'].min()
        if player_df['Batting_AB'].sum() > 0:
            stats['Batting_Career_AVG'] = player_df['Batting_H'].sum() / player_df['Batting_AB'].sum()
        else:
            stats['Batting_Career_AVG'] = None
        stats['Batting_Career_G'] = player_df['Batting_G'].sum()
        stats['Batting_Career_RBI'] = player_df['Batting_RBI'].sum()
        stats['Batting_Career_Num_Seasons'] = len(player_df[player_df['Batting_G'] > 0])

        if (player_df['Batting_HR'].sum() + player_df['Batting_SB'].sum()) > 0:
            stats['Batting_Career_PSN'] = 2 * (player_df['Batting_HR'].sum() * player_df['Batting_SB'].sum()) / (player_df['Batting_HR'].sum() + player_df['Batting_SB'].sum())
        stats['Batting_Career_SB'] = player_df['Batting_SB'].sum()
        stats['Batting_Career_HR'] = player_df['Batting_HR'].sum()
        stats['Batting_Career_TB'] = player_df['Batting_TB'].sum()
        stats['Batting_Career_R'] = player_df['Batting_R'].sum()
        stats['Batting_Career_H'] = player_df['Batting_H'].sum()
        #if player_df['Batting_H'].sum().isnull():
        stats['Batting_Career_2B'] = player_df['Batting_2B'].sum()
        stats['Batting_Career_3B'] = player_df['Batting_3B'].sum()
        if player_df['Batting_AB'].sum() > 0:
            stats['Batting_Career_SLG'] = player_df['Batting_TB'].sum() / player_df['Batting_AB'].sum()

        # OBP
        # On Base Percentage (aka OBP, On Base Average, OBA) is a measure of how often a batter reaches base.
        # It is approximately equal to Times on Base/Plate appearances.
        # The full formula is OBP = (Hits + Walks + Hit by Pitch) / (At Bats + Walks + Hit by Pitch + Sacrifice Flies).

        plate_appearances = player_df['Batting_AB'].sum() + player_df['Batting_BB'].sum() + player_df['Batting_HBP'].sum() + player_df['Batting_SF'].sum()
        if plate_appearances > 0:
            times_on_base = player_df['Batting_BB'].sum() + player_df['Batting_H'].sum() + player_df['Batting_HBP'].sum()
            stats['Batting_Career_OBP'] = times_on_base / plate_appearances

        # Fielding career stats
        stats['Fielding_Career_Max_FPCT'] = player_df['Fielding_FPCT'].max()
        stats['Fielding_Career_Min_FPCT'] = player_df['Fielding_FPCT'].min()

        if (player_df['Fielding_TC'].sum() > 0):
            stats['Fielding_Career_FPCT'] = (player_df['Fielding_PO'].sum() + player_df['Fielding_A'].sum()) / player_df['Fielding_TC'].sum()
        else:
            stats['Fielding_Career_FPCT'] = None
        stats['Fielding_Career_G'] = player_df['Fielding_G'].sum()
        stats['Fielding_Career_Num_Seasons'] = len(player_df[player_df['Fielding_G'] > 0])
        stats['Fielding_Career_A'] = player_df['Fielding_A'].sum()
        stats['Fielding_Career_PO'] = player_df['Fielding_PO'].sum()
        stats['Fielding_Career_E'] = player_df['Fielding_E'].sum()

        # Pitching
        stats['Pitching_Career_Max_ERA'] = player_df['Pitching_ERA'].max()
        stats['Pitching_Career_Min_ERA'] = player_df['Pitching_ERA'].min()

        if (player_df['Pitching_IP'].sum() > 0):
            stats['Pitching_Career_ERA'] = 9 * player_df['Pitching_ER'].sum() / player_df['Pitching_IP'].sum()
        else:
            stats['Pitching_Career_ERA'] = None # or Nan?

        stats['Pitching_Career_IP'] = player_df['Pitching_IP'].sum()
        stats['Pitching_Career_G'] = player_df['Pitching_G'].sum()
        stats['Pitching_Career_Num_Seasons'] = len(player_df[player_df['Pitching_G'] > 0])
        stats['Pitching_Career_ER'] = player_df['Pitching_ER'].sum()
        stats['Pitching_Career_SO'] = player_df['Pitching_SO'].sum()
        stats['Pitching_Career_SHO'] = player_df['Pitching_SHO'].sum()
        stats['Pitching_Career_W'] = player_df['Pitching_W'].sum()
        stats['Pitching_Career_L'] = player_df['Pitching_L'].sum()
        stats['Pitching_Career_GS'] = player_df['Pitching_GS'].sum()
        observations.append(stats)
    else:
        print("No performance stats found.")

    # All star appearances
    subset_ind = (allstar_df['playerID'] == player_id)
    if args.include_current_year:
        subset_ind &= (allstar_df['yearID'] <= salary_year)
    else:
        subset_ind &= (allstar_df['yearID'] < salary_year)
    stats['Num_All_Star_Appearances'] = len(allstar_df[subset_ind].index)

    # Post season
    subset_ind = (performance_post_season_df['playerID'] == player_id)
    if args.include_current_year:
        subset_ind &= (performance_post_season_df['yearID'] <= salary_year)
    else:
        subset_ind &= (performance_post_season_df['yearID'] < salary_year)
    stats['Num_Post_Season_Appearances'] = len(performance_post_season_df[subset_ind].index)

print("Creating data frame...")
cols = []

for obs in observations:
    cols.extend(list(obs.keys()))
cols = list(set(cols))
cols.sort()
cols.insert(0, 'Player Id')
cols.remove('Annual Salary')
cols.remove('Salary Year')
cols.remove('Salary Team')
cols.insert(1, 'Salary Year')
cols.insert(2, 'Annual Salary')
cols.insert(3, 'Salary Team')

num_missing_batting_hits = 0
import csv
with open(os.path.join("..", "data", "db", "Observations.csv"), "w") as obs_out:
    writer = csv.DictWriter(obs_out, cols)
    writer.writeheader()
    for obs in observations:
        if (obs.get('Batting_Career_H') is None):
            num_missing_batting_hits += 1
        writer.writerow(obs)

print("Num missing batting hits: {}".format(num_missing_batting_hits))
print("{} observations written to Observations.csv".format(len(observations)))
print(str(len(salaries_df)) + " salaries.")
print("{} missing players".format(len(missing_players)))
print(metastats)


