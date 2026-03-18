"""
Monte Carlo simulation engine for NCAA bracket prediction.

Runs thousands of tournament simulations to estimate:
- Championship win probabilities for each team
- Round-by-round advancement probabilities
- Most likely bracket outcomes
- Consensus "best bracket" pick
"""

import time
import copy
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

import numpy as np

from bracket import BracketSimulation, REGIONS, ROUND_NAMES


class MonteCarloSimulator:
    """
    Monte Carlo engine for NCAA tournament simulation.
    Runs N simulations and aggregates statistics.
    """

    def __init__(self,
                 data_path: str = "data/teams.json",
                 n_simulations: int = 100_000,
                 upset_factor: float = 1.0,
                 seed: Optional[int] = None):
        """
        Args:
            data_path: Path to teams JSON data file
            n_simulations: Number of Monte Carlo iterations
            upset_factor: Multiplier for upset likelihood (1.0=historical, >1=more upsets)
            seed: Random seed for reproducibility
        """
        self.data_path = data_path
        self.n_simulations = n_simulations
        self.upset_factor = upset_factor
        self.rng_seed = seed
        self.bracket_sim = BracketSimulation(data_path)

        # Storage for simulation results
        self.results: List[Dict] = []
        self.stats: Optional[Dict] = None

    def run(self, verbose: bool = True) -> Dict:
        """
        Run all Monte Carlo simulations.

        Returns aggregated statistics.
        """
        if verbose:
            print(f"\nRunning {self.n_simulations:,} Monte Carlo simulations...")
            print(f"Upset factor: {self.upset_factor}x  |  Random seed: {self.rng_seed}")
            print("-" * 60)

        start_time = time.time()

        # Use a seeded RNG for reproducibility
        rng = np.random.default_rng(self.rng_seed)

        # Track per-team statistics
        team_stats = self._initialize_team_stats()

        # Run simulations
        batch_size = max(1000, self.n_simulations // 20)
        completed = 0

        for batch_start in range(0, self.n_simulations, batch_size):
            batch_end = min(batch_start + batch_size, self.n_simulations)
            batch_count = batch_end - batch_start

            for _ in range(batch_count):
                result = self.bracket_sim.run(rng)
                self._accumulate_stats(team_stats, result)
                completed += 1

            if verbose:
                pct = 100.0 * completed / self.n_simulations
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                print(f"  Progress: {completed:>8,} / {self.n_simulations:,}  "
                      f"({pct:5.1f}%)  |  {rate:,.0f} sims/sec", end='\r')

        elapsed = time.time() - start_time

        if verbose:
            print(f"\n  Completed {completed:,} simulations in {elapsed:.2f}s  "
                  f"({completed/elapsed:,.0f} sims/sec)")
            print("-" * 60)

        # Compute final statistics
        self.stats = self._compute_statistics(team_stats, self.n_simulations)

        return self.stats

    def _initialize_team_stats(self) -> Dict:
        """Initialize per-team statistics counters."""
        stats = {}
        for team in self.bracket_sim.teams_data:
            name = team['name']
            stats[name] = {
                'team': team,
                'first_four_wins': 0,
                'round_appearances': defaultdict(int),  # round_name -> count
                'champion_count': 0,
                'finalist_count': 0,
                'final_four_count': 0,
                'elite_eight_count': 0,
                'sweet_sixteen_count': 0,
            }
        return stats

    def _accumulate_stats(self, team_stats: Dict, result: Dict) -> None:
        """Accumulate statistics from a single simulation result."""
        # First Four winners
        for ff in result.get('first_four', []):
            winner_name = ff['winner']['name']
            if winner_name in team_stats:
                team_stats[winner_name]['first_four_wins'] += 1

        # Regional rounds
        for region, regional in result['regions'].items():
            for round_name, games in regional['rounds'].items():
                for game in games:
                    winner_name = game['winner']['name']
                    if winner_name in team_stats:
                        team_stats[winner_name]['round_appearances'][round_name] += 1

                        # Track milestone rounds
                        if round_name == 'Sweet 16':
                            team_stats[winner_name]['sweet_sixteen_count'] += 1
                        elif round_name == 'Elite 8':
                            team_stats[winner_name]['elite_eight_count'] += 1

        # Final Four
        national = result['national']
        for semifinal_name, game in national['semifinals'].items():
            winner_name = game['winner']['name']
            if winner_name in team_stats:
                team_stats[winner_name]['final_four_count'] += 1

        # Championship game participants (both finalists)
        champ_game = national['championship']
        for team_key in ['winner', 'loser']:
            team_name = champ_game[team_key]['name']
            if team_name in team_stats:
                team_stats[team_name]['finalist_count'] += 1

        # Champion
        champion_name = national['champion']['name']
        if champion_name in team_stats:
            team_stats[champion_name]['champion_count'] += 1

    def _compute_statistics(self, team_stats: Dict, n_sims: int) -> Dict:
        """Convert raw counts to probabilities and rankings."""
        teams_summary = []

        for name, stats in team_stats.items():
            team = stats['team']

            # Compute advancement probabilities
            adv_probs = {}
            for round_name in ROUND_NAMES.values():
                if round_name == 'First Four':
                    if team.get('first_four', False):
                        adv_probs[round_name] = stats['first_four_wins'] / n_sims
                    else:
                        adv_probs[round_name] = 1.0  # automatic qualifier
                else:
                    count = stats['round_appearances'].get(round_name, 0)
                    adv_probs[round_name] = count / n_sims

            # Override with milestone-specific counts
            sweet_16_prob = stats['sweet_sixteen_count'] / n_sims
            elite_8_prob = stats['elite_eight_count'] / n_sims
            final_four_prob = stats['final_four_count'] / n_sims
            finalist_prob = stats['finalist_count'] / n_sims
            champion_prob = stats['champion_count'] / n_sims

            teams_summary.append({
                'name': name,
                'seed': team['seed'],
                'region': team['region'],
                'conf': team['conf'],
                'record': team['record'],
                'adj_em': team['adj_em'],
                'adj_o': team['adj_o'],
                'adj_d': team['adj_d'],
                'net_ranking': team['net_ranking'],
                'is_first_four': team.get('first_four', False),
                'advancement_probs': adv_probs,
                'sweet_16': sweet_16_prob,
                'elite_8': elite_8_prob,
                'final_four': final_four_prob,
                'finalist': finalist_prob,
                'champion': champion_prob,
            })

        # Sort by championship probability
        teams_summary.sort(key=lambda x: x['champion'], reverse=True)

        # Build consensus bracket (most likely winner at each position)
        consensus = self._build_consensus_bracket(team_stats, n_sims)

        return {
            'n_simulations': n_sims,
            'upset_factor': self.upset_factor,
            'teams': teams_summary,
            'consensus_bracket': consensus,
            'top_champions': teams_summary[:10],
        }

    def _build_consensus_bracket(self, team_stats: Dict, n_sims: int) -> Dict:
        """
        Build the "most likely" bracket by picking the highest-probability
        winner at each game slot across all simulations.
        """
        # For the consensus bracket, we simulate one "deterministic" run
        # by always picking the higher-probability team to win each game
        from models import get_win_probability
        from bracket import BRACKET_SEED_ORDER, build_region, REGIONS

        consensus = {
            'regions': {},
            'final_four': {},
            'champion': None,
        }

        def pick_winner(team_a, team_b, round_num):
            """Pick winner based on win probability (deterministic)."""
            prob = get_win_probability(team_a, team_b, round_num)
            return team_a if prob >= 0.5 else team_b

        # Simulate each region deterministically
        regional_champions = {}

        for region in REGIONS:
            region_teams = self.bracket_sim._build_final_region(
                region,
                self.bracket_sim.teams_data,
                {}  # No first four for consensus (use base seeds)
            )

            # Handle First Four: pick winner by probability
            ff_winners = {}
            for ff in self.bracket_sim.first_four_matchups:
                if ff['region'] == region:
                    seed = ff['seed']
                    team_names = ff['teams']
                    ff_team_pool = {t['name']: t for t in self.bracket_sim.teams_data
                                    if t.get('first_four', False)}
                    t1 = ff_team_pool.get(team_names[0])
                    t2 = ff_team_pool.get(team_names[1])
                    if t1 and t2:
                        winner = pick_winner(t1, t2, 0)
                        ff_winners[(region, seed)] = winner

            # Rebuild with FF winners
            region_teams = self.bracket_sim._build_final_region(
                region, self.bracket_sim.teams_data, ff_winners
            )

            rounds = {}
            current_field = list(region_teams)
            round_num = 1

            while len(current_field) > 1:
                next_field = []
                round_results = []
                for i in range(0, len(current_field), 2):
                    winner = pick_winner(current_field[i], current_field[i+1], round_num)
                    round_results.append({
                        'team_a': current_field[i],
                        'team_b': current_field[i+1],
                        'winner': winner,
                    })
                    next_field.append(winner)
                rounds[ROUND_NAMES[round_num]] = round_results
                current_field = next_field
                round_num += 1

            regional_champions[region] = current_field[0]
            consensus['regions'][region] = {
                'rounds': rounds,
                'champion': current_field[0],
            }

        # Final Four (East vs West, South vs Midwest)
        ff_matchups = [
            ('East', 'West'),
            ('South', 'Midwest'),
        ]
        finalists = []
        for r_a, r_b in ff_matchups:
            winner = pick_winner(regional_champions[r_a], regional_champions[r_b], 5)
            consensus['final_four'][f"{r_a} vs {r_b}"] = {
                'team_a': regional_champions[r_a],
                'team_b': regional_champions[r_b],
                'winner': winner,
            }
            finalists.append(winner)

        # Championship
        champion = pick_winner(finalists[0], finalists[1], 6)
        consensus['championship'] = {
            'team_a': finalists[0],
            'team_b': finalists[1],
            'winner': champion,
        }
        consensus['champion'] = champion

        return consensus

    def get_team_stats(self, team_name: str) -> Optional[Dict]:
        """Get simulation statistics for a specific team."""
        if self.stats is None:
            return None
        for team in self.stats['teams']:
            if team['name'].lower() == team_name.lower():
                return team
        return None

    def get_region_rankings(self, region: str) -> List[Dict]:
        """Get teams ranked by championship probability within a region."""
        if self.stats is None:
            return []
        return [t for t in self.stats['teams'] if t['region'] == region]
