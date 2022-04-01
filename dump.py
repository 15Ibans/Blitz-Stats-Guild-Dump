import configparser
import requests
import time
import csv
from pathlib import Path
from datetime import datetime

CONFIG_FILE = "config.ini"
HYPIXEL_API = "https://api.hypixel.net"
HYPIXEL_API_KEY = ""
GUILD_PLAYER = ""  # the player we reference to get the guild information
MOJANG_API = "https://api.mojang.com/users/profiles/minecraft/"
MOJANG_SESSION_API = "https://sessionserver.mojang.com/session/minecraft/profile/"

DELAY = 0.55    # 0.55 seconds


class GuildPlayer:
    def __init__(self, name, kills, deaths, solo_wins, team_wins, games_played):
        self.name = name
        self.kills = kills
        self.deaths = deaths
        self.solo_wins = solo_wins
        self.team_wins = team_wins
        self.games_played = games_played

    def get_kdr(self):
        return round(divide_or_default(self.kills, self.deaths), 2)

    def get_wl(self):
        return round(divide_or_default(self.get_total_wins(), self.deaths), 2)

    def get_kw(self):
        return round(divide_or_default(self.kills, self.get_total_wins()), 2)

    def get_total_wins(self):
        return self.solo_wins + self.team_wins


def divide_or_default(first, second, default=0):
    if second == 0:
        return default
    return first / second


def startup():
    config = configparser.ConfigParser()
    file = Path(CONFIG_FILE)
    exists = file.exists()

    if exists:
        config.read(CONFIG_FILE)
        global HYPIXEL_API_KEY
        HYPIXEL_API_KEY = config["SETTINGS"]["apikey"]
        global GUILD_PLAYER
        GUILD_PLAYER = config["SETTINGS"]["guildplayer"]
    else:
        config["SETTINGS"] = {}
        config["SETTINGS"]["apikey"] = "API Key goes here..."
        config["SETTINGS"]["guildplayer"] = "Guild player goes here..."

        with open(CONFIG_FILE, 'w') as config_file:
            config.write(config_file)
        print("Config file didn't exist, so one was created. Be sure to edit the file before launching again")
        input("Press any key to exit")

    return exists


def scrape_data():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"})

    player_uuid = session.get(MOJANG_API + GUILD_PLAYER).json()["id"]
    print("uuid is " + player_uuid)
    print("api key is " + HYPIXEL_API_KEY)
    hypixel_response = session.get(f"{HYPIXEL_API}/guild", params={"key": HYPIXEL_API_KEY, "player": player_uuid})
    if hypixel_response.status_code != 200:
        print("response code is not 200, but is " + str(hypixel_response.status_code))
        return  # api didn't work here

    guild_json = hypixel_response.json()
    guild_members = guild_json["guild"]["members"]
    guild_name = guild_json["guild"]["name"].replace(" ", "_")
    print("guild name is " + guild_name)
    guild_members_count = len(guild_members)
    guild_players = []

    for i, guild_member in enumerate(guild_json["guild"]["members"]):
        guild_member_uuid = guild_member["uuid"]
        guild_member_stats = session.get(f"{HYPIXEL_API}/player", params={"key": HYPIXEL_API_KEY, "uuid": guild_member_uuid})
        if guild_member_stats.status_code != 200:
            print("Unable to get stats for player with uuid " + guild_member_uuid)
            continue

        guild_member_stats_json = guild_member_stats.json()["player"]
        guild_member_name = guild_member_stats_json["displayname"]
        guild_member_game_stats = guild_member_stats_json["stats"]
        guild_member_blitz_stats = guild_member_game_stats.get("HungerGames")

        if guild_member_blitz_stats is None:
            guild_players.append(GuildPlayer(guild_member_name, 0, 0, 0, 0))
            continue

        guild_member_kills = guild_member_blitz_stats.get("kills", 0)
        guild_member_deaths = guild_member_blitz_stats.get("deaths", 0)
        guild_member_solo_wins = guild_member_blitz_stats.get("wins_solo_normal", 0)
        guild_member_team_wins = guild_member_blitz_stats.get("wins_teams_normal", 0)
        guild_member_games_played = guild_member_blitz_stats.get("games_played", 0)

        guild_players.append(GuildPlayer(guild_member_name, guild_member_kills, guild_member_deaths, guild_member_solo_wins, guild_member_team_wins, guild_member_games_played))
        print(f"({i + 1}/{guild_members_count}) Processed {guild_member_name}")

        time.sleep(DELAY)   # to fit rate limit of max 120 reqs/min

    # save data to a csv
    print("Saving data to csv file...")
    csv_file_name = f"{guild_name}-Guild_Stats_{datetime.today().strftime('%Y-%m-%d')}.csv"
    with open(csv_file_name, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Username", "Kills", "Deaths", "Total Wins", "Solo Wins", "Team Wins" , "K/D", "W/L", "K/W"])
        for player in guild_players:
            writer.writerow([player.name, player.kills, player.deaths, player.get_total_wins(), player.solo_wins, player.team_wins, player.get_kdr(), player.get_wl(), player.get_kw()])


def main():
    if not startup() or len(GUILD_PLAYER) <= 0 or len(HYPIXEL_API_KEY) <= 0:
        return
    scrape_data()


main()
