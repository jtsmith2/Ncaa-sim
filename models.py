"""
Win probability models for NCAA bracket simulation.

Uses multiple approaches:
1. KenPom-style efficiency margin model (primary)
2. Seed-based historical probability (calibration)
3. Combined ensemble model
"""

import math
import numpy as np
from typing import Dict, Tuple

# Historical NCAA tournament win rates by seed matchup (from 1985-2025 data)
# Format: {(seed_favorite, seed_underdog): win_rate_of_favorite}
HISTORICAL_SEED_WIN_RATES: Dict[Tuple[int, int], float] = {
    (1, 16): 0.993,
    (1, 9):  0.848,
    (2, 15): 0.943,
    (2, 10): 0.762,
    (3, 14): 0.849,
    (3, 11): 0.639,
    (4, 13): 0.793,
    (4, 12): 0.638,
    (5, 12): 0.643,
    (5, 13): 0.790,
    (6, 11): 0.621,
    (6, 14): 0.845,
    (7, 10): 0.607,
    (7, 15): 0.944,
    (8, 9):  0.519,
    (8, 16): 0.993,
    (1, 8):  0.773,
    (1, 5):  0.704,
    (2, 7):  0.674,
    (3, 6):  0.624,
    (4, 5):  0.559,
    # Elite Eight
    (1, 4):  0.652,
    (1, 3):  0.590,
    (2, 3):  0.537,
    (2, 4):  0.598,
    # Final Four / Championship (seed advantage still matters but less)
    (1, 2):  0.555,
}


def sigmoid(x: float) -> float:
    """Standard sigmoid function."""
    return 1.0 / (1.0 + math.exp(-x))


def efficiency_margin_win_prob(team_a_em: float, team_b_em: float,
                                k: float = 0.138) -> float:
    """
    Calculate win probability using adjusted efficiency margins.

    The 'k' parameter was calibrated to match historical NCAA tournament results.
    Higher k = stronger favorite effect.

    P(A beats B) = sigmoid(k * (EM_A - EM_B))

    k=0.138 means a 10-point EM difference ≈ 75% win probability for the favorite.
    """
    delta = team_a_em - team_b_em
    return sigmoid(k * delta)


def pythagorean_win_prob(team_a: dict, team_b: dict, exp: float = 11.5) -> float:
    """
    Basketball Pythagorean win probability.
    Uses adjusted offensive and defensive efficiency ratings.

    Pythagorean expectation: W% = O^exp / (O^exp + D^exp)
    For matchup: relative strengths are combined.
    """
    # Effective scoring rates against each other
    # team_a's offense vs team_b's defense (relative to avg=100)
    a_eff_score = (team_a['adj_o'] / 100.0) * (100.0 / team_b['adj_d'])
    b_eff_score = (team_b['adj_o'] / 100.0) * (100.0 / team_a['adj_d'])

    # Pythagorean formula
    a_pyth = a_eff_score ** exp
    b_pyth = b_eff_score ** exp

    return a_pyth / (a_pyth + b_pyth)


def seed_historical_prob(seed_a: int, seed_b: int) -> float:
    """
    Look up historical win probability based on seed matchup.
    Returns probability that team_a (seed_a) beats team_b (seed_b).
    """
    lower_seed = min(seed_a, seed_b)
    higher_seed = max(seed_a, seed_b)

    key = (lower_seed, higher_seed)
    if key in HISTORICAL_SEED_WIN_RATES:
        base_prob = HISTORICAL_SEED_WIN_RATES[key]
        # Return from perspective of team_a
        if seed_a == lower_seed:
            return base_prob
        else:
            return 1.0 - base_prob

    # Fallback: equal seeds or unknown matchup
    if seed_a == seed_b:
        return 0.5

    # Generic fallback based on seed difference
    seed_diff = seed_b - seed_a  # positive means a is better seeded
    return sigmoid(0.1 * seed_diff)


def tempo_adjustment(team_a: dict, team_b: dict) -> float:
    """
    Adjust win probability based on tempo mismatch.

    Fast-paced games increase variance (more possessions = more randomness cancelled out,
    but also more extreme outcomes). Slow games favor the better defensive team.
    Returns a small modifier to apply to the EM-based probability.
    """
    # Game tempo will roughly average the two teams' tempos
    avg_tempo = (team_a['adj_t'] + team_b['adj_t']) / 2.0

    # Lower tempo = more variance per game (fewer possessions)
    # Higher tempo = less variance per game
    # Standard tempo is ~70 possessions
    # Below 66 = slow, above 74 = fast
    tempo_factor = (avg_tempo - 70.0) / 70.0  # small normalized factor

    return tempo_factor


def ensemble_win_probability(team_a: dict, team_b: dict,
                              em_weight: float = 0.60,
                              pyth_weight: float = 0.25,
                              seed_weight: float = 0.15) -> float:
    """
    Ensemble model combining multiple probability estimates.

    Weights:
    - Efficiency margin model: 60% (most predictive)
    - Pythagorean model: 25% (good at capturing O/D balance)
    - Historical seed probability: 15% (captures tournament-specific effects)
    """
    # Primary: Efficiency margin
    p_em = efficiency_margin_win_prob(team_a['adj_em'], team_b['adj_em'])

    # Secondary: Pythagorean
    p_pyth = pythagorean_win_prob(team_a, team_b)

    # Tertiary: Historical seed rates
    p_seed = seed_historical_prob(team_a['seed'], team_b['seed'])

    # Weighted ensemble
    p_ensemble = em_weight * p_em + pyth_weight * p_pyth + seed_weight * p_seed

    # Clamp to reasonable bounds (avoid 0 or 1 probability)
    return max(0.02, min(0.98, p_ensemble))


def apply_upsets_variance(base_prob: float,
                          tournament_round: int,
                          upset_factor: float = 1.0) -> float:
    """
    Apply tournament-specific variance adjustments.

    Later rounds tend to be more competitive (better teams remaining).
    The upset_factor can be tuned for different scenarios.

    Round 1 = First Round, Round 6 = Championship
    """
    # In later rounds, regression to mean (games become more evenly matched)
    # Pull probabilities slightly toward 0.5 in later rounds
    round_regression = {
        1: 0.0,    # No adjustment in first round
        2: 0.01,   # Small regression in second round
        3: 0.025,  # Sweet 16
        4: 0.04,   # Elite 8
        5: 0.055,  # Final Four
        6: 0.065,  # Championship
    }

    regression = round_regression.get(tournament_round, 0.03)
    adjusted = 0.5 + (base_prob - 0.5) * (1.0 - regression * upset_factor)

    return max(0.02, min(0.98, adjusted))


def simulate_game(team_a: dict, team_b: dict,
                  tournament_round: int,
                  rng: np.random.Generator,
                  upset_factor: float = 1.0) -> dict:
    """
    Simulate a single game between two teams.

    Returns dict with winner, loser, and win probability.
    """
    base_prob = ensemble_win_probability(team_a, team_b)
    adj_prob = apply_upsets_variance(base_prob, tournament_round, upset_factor)

    # Sample from Bernoulli distribution
    a_wins = rng.random() < adj_prob

    winner = team_a if a_wins else team_b
    loser = team_b if a_wins else team_a
    win_prob = adj_prob if a_wins else 1.0 - adj_prob

    return {
        'winner': winner,
        'loser': loser,
        'win_probability': win_prob,
        'team_a_win_prob': adj_prob,
        'upset': winner['seed'] > loser['seed'],
    }


def get_win_probability(team_a: dict, team_b: dict,
                         tournament_round: int = 1,
                         upset_factor: float = 1.0) -> float:
    """Get win probability for team_a vs team_b without simulation."""
    base_prob = ensemble_win_probability(team_a, team_b)
    return apply_upsets_variance(base_prob, tournament_round, upset_factor)
