"""
Report generation for NCAA bracket simulation results.

Provides formatted output for:
- Championship odds table
- Consensus bracket display
- Regional breakdowns
- Upset probability analysis
"""

from typing import Dict, List, Optional
from tabulate import tabulate

from bracket import REGIONS, ROUND_NAMES


# ANSI color codes for terminal output
RESET   = "\033[0m"
BOLD    = "\033[1m"
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
GRAY    = "\033[90m"

REGION_COLORS = {
    "East":    BLUE,
    "South":   RED,
    "Midwest": GREEN,
    "West":    YELLOW,
}


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a probability as a percentage string."""
    return f"{value * 100:.{decimals}f}%"


def color_prob(prob: float) -> str:
    """Color-code a probability value."""
    pct = prob * 100
    if pct >= 25:
        color = GREEN
    elif pct >= 10:
        color = YELLOW
    elif pct >= 3:
        color = CYAN
    else:
        color = GRAY
    return f"{color}{pct:5.1f}%{RESET}"


def print_header(title: str, width: int = 80) -> None:
    """Print a section header."""
    border = "=" * width
    print(f"\n{BOLD}{border}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{border}{RESET}")


def print_subheader(title: str, width: int = 60) -> None:
    """Print a section subheader."""
    print(f"\n{BOLD}{CYAN}{'─' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")


def print_championship_odds(stats: Dict, top_n: int = 20) -> None:
    """Print championship odds table for top N teams."""
    print_header("2026 NCAA TOURNAMENT - CHAMPIONSHIP ODDS (Monte Carlo)")
    print(f"  {GRAY}Based on {stats['n_simulations']:,} simulations  |  "
          f"Upset factor: {stats['upset_factor']}x{RESET}\n")

    teams = stats['teams'][:top_n]

    headers = ["Rank", "Team", "Seed", "Region", "Record", "AdjEM",
               "S16", "E8", "F4", "Final", "Champion"]
    rows = []

    for i, team in enumerate(teams, 1):
        region_color = REGION_COLORS.get(team['region'], WHITE)
        region_str = f"{region_color}{team['region']}{RESET}"

        seed_color = BOLD if team['seed'] <= 4 else RESET
        seed_str = f"{seed_color}{team['seed']:>2}{RESET}"

        champ_pct = team['champion'] * 100
        if champ_pct >= 20:
            champ_str = f"{GREEN}{BOLD}{champ_pct:5.1f}%{RESET}"
        elif champ_pct >= 10:
            champ_str = f"{GREEN}{champ_pct:5.1f}%{RESET}"
        elif champ_pct >= 5:
            champ_str = f"{YELLOW}{champ_pct:5.1f}%{RESET}"
        else:
            champ_str = f"{CYAN}{champ_pct:5.1f}%{RESET}"

        rows.append([
            f"#{i}",
            f"{BOLD}{team['name']}{RESET}",
            seed_str,
            region_str,
            team['record'],
            f"{team['adj_em']:+.1f}",
            fmt_pct(team['sweet_16']),
            fmt_pct(team['elite_8']),
            fmt_pct(team['final_four']),
            fmt_pct(team['finalist']),
            champ_str,
        ])

    print(tabulate(rows, headers=headers, tablefmt="simple", colalign=(
        "right", "left", "right", "left", "center",
        "right", "right", "right", "right", "right", "right"
    )))


def print_full_odds_table(stats: Dict) -> None:
    """Print full odds table for all teams sorted by region and seed."""
    print_header("ALL TEAMS - ADVANCEMENT PROBABILITIES")

    for region in REGIONS:
        region_color = REGION_COLORS.get(region, WHITE)
        print(f"\n  {region_color}{BOLD}{'─'*10} {region} Region {'─'*10}{RESET}")

        region_teams = sorted(
            [t for t in stats['teams'] if t['region'] == region],
            key=lambda x: x['seed']
        )

        headers = ["Seed", "Team", "Conf", "Record", "AdjEM",
                   "R32", "S16", "E8", "F4", "Final", "Champ"]
        rows = []

        for team in region_teams:
            # Get first round win probability
            r32 = team['advancement_probs'].get('First Round', 0)

            rows.append([
                team['seed'],
                team['name'] + (" *" if team['is_first_four'] else ""),
                team['conf'],
                team['record'],
                f"{team['adj_em']:+.1f}",
                fmt_pct(r32),
                fmt_pct(team['sweet_16']),
                fmt_pct(team['elite_8']),
                fmt_pct(team['final_four']),
                fmt_pct(team['finalist']),
                fmt_pct(team['champion']),
            ])

        print(tabulate(rows, headers=headers, tablefmt="simple"))
        print(f"  {GRAY}* = First Four participant{RESET}")


def print_consensus_bracket(stats: Dict) -> None:
    """Display the consensus (most likely) bracket picks."""
    print_header("CONSENSUS BRACKET - MOST LIKELY PICKS")

    consensus = stats['consensus_bracket']

    print(f"  {GRAY}This bracket picks the statistically most likely winner "
          f"at each game position.{RESET}\n")

    for region in REGIONS:
        region_color = REGION_COLORS.get(region, WHITE)
        print(f"\n{region_color}{BOLD}  ═══ {region.upper()} REGION ═══{RESET}")

        region_data = consensus['regions'].get(region, {})
        rounds = region_data.get('rounds', {})

        round_order = ['First Round', 'Second Round', 'Sweet 16', 'Elite 8']

        for round_name in round_order:
            if round_name not in rounds:
                continue

            games = rounds[round_name]
            print(f"\n  {BOLD}{round_name}:{RESET}")

            for game in games:
                t_a = game['team_a']
                t_b = game['team_b']
                winner = game['winner']

                a_str = f"({t_a['seed']}) {t_a['name']}"
                b_str = f"({t_b['seed']}) {t_b['name']}"

                if winner['name'] == t_a['name']:
                    win_str = f"{GREEN}{BOLD}{a_str}{RESET}"
                    lose_str = f"{GRAY}{b_str}{RESET}"
                else:
                    win_str = f"{GREEN}{BOLD}{b_str}{RESET}"
                    lose_str = f"{GRAY}{a_str}{RESET}"

                print(f"    {win_str}  def.  {lose_str}")

        champion = region_data.get('champion', {})
        if champion:
            print(f"\n  {region_color}{BOLD}  Regional Champion: "
                  f"({champion['seed']}) {champion['name']}{RESET}")

    # Final Four
    print(f"\n{MAGENTA}{BOLD}  ═══ FINAL FOUR ═══{RESET}")
    for matchup, game in consensus['final_four'].items():
        t_a = game['team_a']
        t_b = game['team_b']
        winner = game['winner']

        a_str = f"({t_a['seed']}) {t_a['name']} [{t_a['region']}]"
        b_str = f"({t_b['seed']}) {t_b['name']} [{t_b['region']}]"

        if winner['name'] == t_a['name']:
            print(f"\n  {GREEN}{BOLD}{a_str}{RESET}  def.  {GRAY}{b_str}{RESET}")
        else:
            print(f"\n  {GRAY}{a_str}{RESET}  def.  {GREEN}{BOLD}{b_str}{RESET}")

    # Championship
    champ_game = consensus.get('championship', {})
    if champ_game:
        print(f"\n{YELLOW}{BOLD}  ═══ NATIONAL CHAMPIONSHIP ═══{RESET}")
        t_a = champ_game['team_a']
        t_b = champ_game['team_b']
        winner = champ_game['winner']
        loser = t_b if winner['name'] == t_a['name'] else t_a

        print(f"\n  {GREEN}{BOLD}  CHAMPION: ({winner['seed']}) {winner['name']} "
              f"[{winner['region']}]{RESET}")
        print(f"  {GRAY}  Defeats: ({loser['seed']}) {loser['name']} "
              f"[{loser['region']}]{RESET}")


def print_upset_analysis(stats: Dict) -> None:
    """Print analysis of likely upsets and Cinderella candidates."""
    print_header("UPSET & CINDERELLA ANALYSIS")

    # Teams with seed >= 10 that have notable advancement chances
    upsets = []
    for team in stats['teams']:
        if team['seed'] >= 10 and team['sweet_16'] >= 0.05:
            upsets.append(team)

    upsets.sort(key=lambda x: x['sweet_16'], reverse=True)

    if upsets:
        print_subheader("Cinderella Candidates (Seed 10+, >5% Sweet 16 chance)")
        headers = ["Team", "Seed", "Region", "AdjEM", "S16", "E8", "F4", "Champ"]
        rows = []
        for team in upsets[:12]:
            rows.append([
                team['name'],
                team['seed'],
                team['region'],
                f"{team['adj_em']:+.1f}",
                fmt_pct(team['sweet_16']),
                fmt_pct(team['elite_8']),
                fmt_pct(team['final_four']),
                fmt_pct(team['champion']),
            ])
        print(tabulate(rows, headers=headers, tablefmt="simple"))

    # First round upset risks (seeds 1-4 with < expected win rate)
    print_subheader("High-Seed First Round Upset Risks")
    upset_risks = []
    for team in stats['teams']:
        if team['seed'] <= 5:
            r1_prob = team['advancement_probs'].get('First Round', 0)
            expected = {1: 0.993, 2: 0.943, 3: 0.849, 4: 0.793, 5: 0.643}.get(team['seed'], 0.7)
            if r1_prob < expected * 0.92:  # >8% below historical average
                upset_risks.append({
                    **team,
                    'r1_prob': r1_prob,
                    'expected': expected,
                    'risk': expected - r1_prob,
                })

    if upset_risks:
        upset_risks.sort(key=lambda x: x['risk'], reverse=True)
        headers = ["Team", "Seed", "R1 Win%", "Historical Avg", "Upset Risk"]
        rows = []
        for team in upset_risks[:8]:
            rows.append([
                team['name'],
                f"({team['seed']})",
                fmt_pct(team['r1_prob']),
                fmt_pct(team['expected']),
                f"{RED}{fmt_pct(team['risk'])}{RESET}",
            ])
        print(tabulate(rows, headers=headers, tablefmt="simple"))
    else:
        print("  No significant first-round upset risks detected.")


def print_region_summary(stats: Dict) -> None:
    """Print a quick summary of each region's favorites."""
    print_header("REGIONAL FAVORITES SUMMARY")

    for region in REGIONS:
        region_color = REGION_COLORS.get(region, WHITE)
        region_teams = sorted(
            [t for t in stats['teams'] if t['region'] == region],
            key=lambda x: x['champion'],
            reverse=True
        )

        print(f"\n  {region_color}{BOLD}{region} Region{RESET}")

        headers = ["Rank", "Team", "Seed", "Elite 8", "Final Four", "Champion"]
        rows = []
        for i, team in enumerate(region_teams[:5], 1):
            rows.append([
                f"#{i}",
                team['name'],
                f"({team['seed']})",
                fmt_pct(team['elite_8']),
                fmt_pct(team['final_four']),
                color_prob(team['champion']),
            ])
        print(tabulate(rows, headers=headers, tablefmt="simple"))


def print_matchup_preview(team_a: dict, team_b: dict, n_sims: int = 10000) -> None:
    """
    Print a head-to-head matchup analysis.
    """
    from models import ensemble_win_probability, efficiency_margin_win_prob

    p = ensemble_win_probability(team_a, team_b)
    print(f"\n{BOLD}Head-to-Head Matchup Preview{RESET}")
    print(f"  {team_a['name']} (#{team_a['seed']} {team_a['region']}) "
          f"vs {team_b['name']} (#{team_b['seed']} {team_b['region']})")
    print(f"\n  {'Metric':<20} {'':>15} {'':>15}")
    print(f"  {'─'*50}")
    print(f"  {'Team':<20} {team_a['name']:>15} {team_b['name']:>15}")
    print(f"  {'Seed':<20} {team_a['seed']:>15} {team_b['seed']:>15}")
    print(f"  {'Record':<20} {team_a['record']:>15} {team_b['record']:>15}")
    print(f"  {'Adj. EM':<20} {team_a['adj_em']:>+14.1f} {team_b['adj_em']:>+14.1f}")
    print(f"  {'Adj. O':<20} {team_a['adj_o']:>14.1f} {team_b['adj_o']:>14.1f}")
    print(f"  {'Adj. D':<20} {team_a['adj_d']:>14.1f} {team_b['adj_d']:>14.1f}")
    print(f"\n  {BOLD}Win Probability: {GREEN}{p*100:.1f}%{RESET} "
          f"{team_a['name']} | {RED}{(1-p)*100:.1f}%{RESET} {team_b['name']}")


def print_full_report(stats: Dict, compact: bool = False) -> None:
    """Print the full simulation report."""
    print_championship_odds(stats, top_n=20)

    if not compact:
        print_region_summary(stats)
        print_full_odds_table(stats)
        print_upset_analysis(stats)

    print_consensus_bracket(stats)

    print(f"\n{BOLD}{GREEN}{'═' * 70}{RESET}")
    champion = stats['consensus_bracket']['champion']
    champ_stats = next(
        (t for t in stats['teams'] if t['name'] == champion['name']), {}
    )
    print(f"{BOLD}{GREEN}  PREDICTED CHAMPION: ({champion['seed']}) "
          f"{champion['name']} — {fmt_pct(champ_stats.get('champion', 0))} "
          f"championship probability{RESET}")
    print(f"{BOLD}{GREEN}{'═' * 70}{RESET}\n")
