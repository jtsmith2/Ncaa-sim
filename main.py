#!/usr/bin/env python3
"""
NCAA Tournament Monte Carlo Bracket Simulator - 2026
=====================================================

Simulates the NCAA Men's Basketball Tournament using Monte Carlo methods
and team statistics (KenPom-style efficiency metrics) to predict the most
likely bracket outcomes.

Usage:
    python main.py                          # Run with defaults (100k sims)
    python main.py --sims 50000             # Custom simulation count
    python main.py --seed 42                # Reproducible results
    python main.py --upset-factor 1.5       # More upsets
    python main.py --compact                # Condensed output
    python main.py --matchup "Duke" "Auburn" # Head-to-head analysis
    python main.py --team "Duke"            # Team-specific stats
    python main.py --save results.json      # Save results to file
"""

import argparse
import json
import sys
import os
from pathlib import Path

from simulator import MonteCarloSimulator
from report import (
    print_full_report,
    print_championship_odds,
    print_consensus_bracket,
    print_matchup_preview,
    print_header,
    BOLD, RESET, CYAN, GREEN, YELLOW, RED, GRAY,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="2026 NCAA Tournament Monte Carlo Bracket Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--sims", "-n",
        type=int,
        default=100_000,
        help="Number of Monte Carlo simulations to run (default: 100,000)",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed for reproducible results",
    )
    parser.add_argument(
        "--upset-factor", "-u",
        type=float,
        default=1.0,
        dest="upset_factor",
        help="Upset likelihood multiplier (1.0=historical, >1=more upsets, default: 1.0)",
    )
    parser.add_argument(
        "--compact", "-c",
        action="store_true",
        help="Print condensed report (skip full odds table)",
    )
    parser.add_argument(
        "--matchup", "-m",
        nargs=2,
        metavar=("TEAM_A", "TEAM_B"),
        help="Print head-to-head matchup analysis for two teams",
    )
    parser.add_argument(
        "--team", "-t",
        type=str,
        help="Print detailed stats for a specific team",
    )
    parser.add_argument(
        "--save",
        type=str,
        metavar="FILE",
        help="Save simulation results to JSON file",
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data/teams.json",
        help="Path to teams data JSON file",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of top teams to show in championship odds table (default: 20)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored terminal output",
    )

    return parser.parse_args()


def print_team_detail(team_stats: dict, sim_stats: dict) -> None:
    """Print detailed simulation stats for a single team."""
    print_header(f"TEAM DETAIL: {team_stats['name'].upper()}")

    t = team_stats
    print(f"\n  {BOLD}{'─'*40}{RESET}")
    print(f"  {'Team:':<20} {BOLD}{t['name']}{RESET}")
    print(f"  {'Seed:':<20} #{t['seed']} {t['region']} Region")
    print(f"  {'Conference:':<20} {t['conf']}")
    print(f"  {'Record:':<20} {t['record']}")
    print(f"  {'NET Ranking:':<20} #{t['net_ranking']}")
    print(f"\n  {BOLD}Season Stats (KenPom-style){RESET}")
    print(f"  {'Adj. Efficiency Margin:':<30} {t['adj_em']:+.1f}")
    print(f"  {'Adj. Offensive Eff.:':<30} {t['adj_o']:.1f} pts/100 poss")
    print(f"  {'Adj. Defensive Eff.:':<30} {t['adj_d']:.1f} pts allowed/100 poss")
    print(f"\n  {BOLD}Tournament Advancement Probabilities{RESET}")
    print(f"  {'─'*40}")

    milestones = [
        ("First Round Win",    "sweet_16",    None),
        ("Sweet 16",           "sweet_16",    None),
        ("Elite 8",            "elite_8",     None),
        ("Final Four",         "final_four",  None),
        ("Championship Game",  "finalist",    None),
        ("NATIONAL CHAMPION",  "champion",    GREEN),
    ]

    # First round prob
    r1 = t['advancement_probs'].get('First Round', 1.0)
    print(f"  {'First Round Win':<30} {r1*100:6.1f}%")

    for label, key, color in milestones[1:]:
        prob = t[key]
        pct = prob * 100
        if color:
            print(f"  {BOLD}{label:<30}{RESET} {color}{pct:6.1f}%{RESET}")
        elif pct >= 25:
            print(f"  {label:<30} {GREEN}{pct:6.1f}%{RESET}")
        elif pct >= 10:
            print(f"  {label:<30} {YELLOW}{pct:6.1f}%{RESET}")
        elif pct >= 3:
            print(f"  {label:<30} {CYAN}{pct:6.1f}%{RESET}")
        else:
            print(f"  {label:<30} {GRAY}{pct:6.1f}%{RESET}")


def save_results(stats: dict, filepath: str) -> None:
    """Save simulation results to JSON, converting to serializable format."""
    # Make a copy with serializable data
    output = {
        'n_simulations': stats['n_simulations'],
        'upset_factor': stats['upset_factor'],
        'champion': stats['consensus_bracket']['champion']['name'],
        'teams': [],
    }

    for team in stats['teams']:
        output['teams'].append({
            'name': team['name'],
            'seed': team['seed'],
            'region': team['region'],
            'conf': team['conf'],
            'record': team['record'],
            'adj_em': team['adj_em'],
            'net_ranking': team['net_ranking'],
            'sweet_16_pct': round(team['sweet_16'] * 100, 2),
            'elite_8_pct': round(team['elite_8'] * 100, 2),
            'final_four_pct': round(team['final_four'] * 100, 2),
            'finalist_pct': round(team['finalist'] * 100, 2),
            'champion_pct': round(team['champion'] * 100, 2),
        })

    # Add consensus bracket
    consensus = stats['consensus_bracket']
    bracket_output = {'regions': {}, 'final_four': {}, 'champion': None}

    for region, data in consensus['regions'].items():
        bracket_output['regions'][region] = {
            'champion': data['champion']['name'],
            'rounds': {}
        }
        for round_name, games in data['rounds'].items():
            bracket_output['regions'][region]['rounds'][round_name] = [
                {
                    'winner': g['winner']['name'],
                    'seed': g['winner']['seed'],
                    'vs': g['team_b']['name'] if g['winner']['name'] == g['team_a']['name']
                          else g['team_a']['name'],
                }
                for g in games
            ]

    for matchup, game in consensus['final_four'].items():
        bracket_output['final_four'][matchup] = game['winner']['name']

    champ_game = consensus.get('championship', {})
    if champ_game:
        bracket_output['champion'] = champ_game['winner']['name']
        bracket_output['championship'] = {
            'winner': champ_game['winner']['name'],
            'loser': (champ_game['team_b']['name']
                      if champ_game['winner']['name'] == champ_game['team_a']['name']
                      else champ_game['team_a']['name']),
        }

    output['consensus_bracket'] = bracket_output

    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n{GREEN}Results saved to: {filepath}{RESET}")


def main():
    args = parse_args()

    # Validate data file
    if not Path(args.data).exists():
        print(f"{RED}Error: Data file not found: {args.data}{RESET}", file=sys.stderr)
        sys.exit(1)

    # Validate upset factor
    if args.upset_factor <= 0 or args.upset_factor > 5:
        print(f"{RED}Error: upset-factor must be between 0 and 5{RESET}", file=sys.stderr)
        sys.exit(1)

    # Handle matchup preview (no simulation needed)
    if args.matchup:
        from bracket import BracketSimulation
        sim = BracketSimulation(args.data)
        t_a = sim.get_team_by_name(args.matchup[0])
        t_b = sim.get_team_by_name(args.matchup[1])

        if t_a is None:
            print(f"{RED}Team not found: {args.matchup[0]}{RESET}", file=sys.stderr)
            sys.exit(1)
        if t_b is None:
            print(f"{RED}Team not found: {args.matchup[1]}{RESET}", file=sys.stderr)
            sys.exit(1)

        print_matchup_preview(t_a, t_b)
        return

    # Run Monte Carlo simulation
    simulator = MonteCarloSimulator(
        data_path=args.data,
        n_simulations=args.sims,
        upset_factor=args.upset_factor,
        seed=args.seed,
    )

    stats = simulator.run(verbose=True)

    # Handle team detail request
    if args.team:
        team_stats = simulator.get_team_stats(args.team)
        if team_stats is None:
            print(f"{RED}Team not found: {args.team}{RESET}", file=sys.stderr)
            sys.exit(1)
        print_team_detail(team_stats, stats)
        return

    # Print full report
    print_full_report(stats, compact=args.compact)

    if not args.compact:
        # Print quick summary at the end
        print(f"\n{BOLD}Quick Summary (Top 5 Championship Picks):{RESET}")
        for i, team in enumerate(stats['teams'][:5], 1):
            bar_len = int(team['champion'] * 200)
            bar = "█" * min(bar_len, 50)
            print(f"  {i}. ({team['seed']:>2}) {team['name']:<20} "
                  f"{team['champion']*100:5.1f}%  {GREEN}{bar}{RESET}")

    # Save results if requested
    if args.save:
        save_results(stats, args.save)


if __name__ == "__main__":
    main()
