"""
NCAA Tournament Bracket structure and single-simulation logic.

Handles:
- Loading the 68-team field
- First Four play-in games
- Regional brackets (64 -> 32 -> 16 -> 8 -> Final Four)
- Final Four and Championship
"""

import json
import copy
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np

from models import simulate_game


# Tournament round names
ROUND_NAMES = {
    0: "First Four",
    1: "First Round",
    2: "Second Round",
    3: "Sweet 16",
    4: "Elite 8",
    5: "Final Four",
    6: "Championship",
}

# Regions
REGIONS = ["East", "South", "Midwest", "West"]

# Standard bracket seeding order — determines who plays who in each region
# Position in region: [1,16,8,9,5,12,4,13,6,11,3,14,7,10,2,15]
# This is the standard NCAA bracket slot order
BRACKET_SEED_ORDER = [1, 16, 8, 9, 5, 12, 4, 13, 6, 11, 3, 14, 7, 10, 2, 15]


def load_teams(data_path: str = "data/teams.json") -> Dict:
    """Load team data from JSON file."""
    path = Path(data_path)
    with open(path) as f:
        return json.load(f)


def build_region(teams_data: List[dict], region: str) -> List[dict]:
    """
    Build a sorted list of 16 teams for a region, ordered by bracket slot.
    Seeds 1-16, arranged so 1 plays 16, 2 plays 15, etc.
    """
    region_teams = [t for t in teams_data if t['region'] == region
                    and not t.get('first_four', False)]

    # Sort by seed
    seed_to_team = {t['seed']: t for t in region_teams}

    # Arrange in bracket slot order
    ordered = []
    for seed in BRACKET_SEED_ORDER:
        if seed in seed_to_team:
            ordered.append(seed_to_team[seed])

    return ordered


def resolve_first_four(teams_data: List[dict],
                       first_four_matchups: List[dict],
                       rng: np.random.Generator) -> List[dict]:
    """
    Simulate First Four games and return the 4 winners to fill
    their spots in the main bracket.
    """
    results = []
    ff_teams = {t['name']: t for t in teams_data if t.get('first_four', False)}

    for matchup in first_four_matchups:
        team_names = matchup['teams']
        if len(team_names) != 2:
            continue

        t1 = ff_teams.get(team_names[0])
        t2 = ff_teams.get(team_names[1])

        if t1 is None or t2 is None:
            continue

        result = simulate_game(t1, t2, tournament_round=0, rng=rng)
        winner = copy.deepcopy(result['winner'])
        winner['first_four_win'] = True
        results.append({
            'region': matchup['region'],
            'seed': matchup['seed'],
            'winner': winner,
            'loser': result['loser'],
            'game': result,
        })

    return results


def simulate_region(region_teams: List[dict],
                    region_name: str,
                    rng: np.random.Generator) -> Dict:
    """
    Simulate a full regional bracket (16 teams -> 1 winner).

    Returns dict with round-by-round results and the regional champion.
    """
    assert len(region_teams) == 16, f"Expected 16 teams, got {len(region_teams)}"

    rounds = {}
    current_field = list(region_teams)

    round_num = 1
    while len(current_field) > 1:
        round_results = []
        next_field = []

        for i in range(0, len(current_field), 2):
            team_a = current_field[i]
            team_b = current_field[i + 1]
            result = simulate_game(team_a, team_b,
                                   tournament_round=round_num, rng=rng)
            round_results.append(result)
            next_field.append(result['winner'])

        rounds[ROUND_NAMES[round_num]] = round_results
        current_field = next_field
        round_num += 1

    champion = current_field[0]
    return {
        'region': region_name,
        'rounds': rounds,
        'champion': champion,
    }


def simulate_final_four(regional_results: Dict[str, dict],
                         rng: np.random.Generator) -> Dict:
    """
    Simulate Final Four and Championship from 4 regional champions.

    NCAA Final Four pairings (standard): East vs West, South vs Midwest
    """
    # Standard Final Four pairings
    semifinal_pairings = [
        ('East', 'West'),
        ('South', 'Midwest'),
    ]

    final_four_results = {}
    finalists = []

    for region_a, region_b in semifinal_pairings:
        team_a = regional_results[region_a]['champion']
        team_b = regional_results[region_b]['champion']

        result = simulate_game(team_a, team_b, tournament_round=5, rng=rng)
        matchup_name = f"{region_a} vs {region_b}"
        final_four_results[matchup_name] = result
        finalists.append(result['winner'])

    # Championship game
    championship = simulate_game(finalists[0], finalists[1],
                                  tournament_round=6, rng=rng)

    return {
        'semifinals': final_four_results,
        'championship': championship,
        'champion': championship['winner'],
    }


class BracketSimulation:
    """
    Represents a single complete NCAA tournament simulation.
    """

    def __init__(self, data_path: str = "data/teams.json"):
        self.data = load_teams(data_path)
        self.teams_data = self.data['teams']
        self.first_four_matchups = self.data['first_four_matchups']

    def run(self, rng: np.random.Generator) -> Dict:
        """
        Run one complete tournament simulation.

        Returns full results dict with all games, rounds, and champion.
        """
        teams = copy.deepcopy(self.teams_data)

        # Step 1: First Four
        ff_results = resolve_first_four(teams, self.first_four_matchups, rng)

        # Replace First Four slots in main bracket
        # For each first_four winner, replace the placeholder team in that region
        ff_winners_by_slot = {}
        for ff in ff_results:
            key = (ff['region'], ff['seed'])
            ff_winners_by_slot[key] = ff['winner']

        # Step 2: Build regional brackets, substituting First Four winners
        regional_results = {}

        for region in REGIONS:
            region_teams = build_region(teams, region)

            # Replace any First Four slots
            for i, team in enumerate(region_teams):
                key = (region, team['seed'])
                if key in ff_winners_by_slot:
                    # Check if this team is a First Four participant
                    if team.get('first_four', False) or team['name'] in [
                        t for ff in self.first_four_matchups
                        if ff['region'] == region
                        for t in ff['teams']
                    ]:
                        region_teams[i] = ff_winners_by_slot[key]

            # Build proper 16-team bracket, filling First Four winner
            final_region_teams = self._build_final_region(region, teams, ff_winners_by_slot)
            regional_results[region] = simulate_region(final_region_teams, region, rng)

        # Step 3: Final Four + Championship
        national_results = simulate_final_four(regional_results, rng)

        return {
            'first_four': ff_results,
            'regions': regional_results,
            'national': national_results,
            'champion': national_results['champion'],
        }

    def _build_final_region(self, region: str,
                             all_teams: List[dict],
                             ff_winners: Dict) -> List[dict]:
        """
        Build final 16-team field for a region, substituting First Four winners.
        """
        # Get regular teams for this region (not first-four participants)
        regular_teams = {
            t['seed']: t for t in all_teams
            if t['region'] == region and not t.get('first_four', False)
        }

        # Check which seeds had First Four games in this region
        ff_seeds_in_region = set()
        for ff in self.first_four_matchups:
            if ff['region'] == region:
                ff_seeds_in_region.add(ff['seed'])

        # Build final roster
        final_teams = {}
        for seed in range(1, 17):
            ff_key = (region, seed)
            if seed in ff_seeds_in_region and ff_key in ff_winners:
                final_teams[seed] = ff_winners[ff_key]
            elif seed in regular_teams:
                final_teams[seed] = regular_teams[seed]

        # Return in bracket slot order
        return [final_teams[seed] for seed in BRACKET_SEED_ORDER if seed in final_teams]

    def get_team_by_name(self, name: str) -> Optional[dict]:
        """Look up a team by name."""
        for team in self.teams_data:
            if team['name'].lower() == name.lower():
                return team
        return None

    def get_teams_by_seed(self, seed: int, region: str = None) -> List[dict]:
        """Get all teams with a given seed, optionally filtered by region."""
        teams = [t for t in self.teams_data if t['seed'] == seed]
        if region:
            teams = [t for t in teams if t['region'] == region]
        return teams
