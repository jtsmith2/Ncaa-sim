# NCAA Tournament Monte Carlo Bracket Simulator — 2026

Predicts the most likely 2026 NCAA Men's Basketball Tournament outcomes by running thousands of simulations using real team statistics. Built for bracket competitions — including a **portfolio mode** that generates 10 strategically diversified brackets to maximize your chances of winning an office pool.

---

## Quick Start

```bash
pip install -r requirements.txt

# Run full simulation (100,000 iterations)
python main.py

# Generate 10 optimized brackets for an office pool
python main.py --portfolio 10

# Faster preview run
python main.py --sims 10000 --compact

# Save results to JSON
python main.py --save results_2026.json
```

---

## How It Works

### Win Probability Model

Each game is simulated using an **ensemble of three models**:

| Model | Weight | Description |
|---|---|---|
| Efficiency Margin | 60% | KenPom-style `sigmoid(k × ΔAdjEM)` — most predictive single metric |
| Pythagorean Expectation | 25% | Offensive/defensive efficiency head-to-head |
| Historical Seed Rates | 15% | 40 years of actual NCAA tournament results (1985–2025) |

Win probabilities are then adjusted per round — later rounds apply slight regression to the mean, since surviving teams are increasingly evenly matched.

### Monte Carlo Engine

- Runs **N independent tournament simulations** (default: 100,000)
- Each simulation independently samples game outcomes using the probability model
- Results aggregate into per-team advancement probabilities across all 6 rounds
- Produces a **consensus bracket** (highest-probability pick at every game slot) and **championship odds** for all 68 teams

### Team Statistics

All 68 teams are rated using **KenPom-style adjusted efficiency metrics**:

- **AdjO** — Adjusted Offensive Efficiency (points per 100 possessions vs. avg defense)
- **AdjD** — Adjusted Defensive Efficiency (points allowed per 100 possessions vs. avg offense)
- **AdjEM** — Adjusted Efficiency Margin (AdjO − AdjD) — the primary rating
- **AdjT** — Adjusted Tempo (possessions per 40 minutes)
- **NET Ranking** — NCAA Evaluation Tool ranking

---

## 2026 Predictions (100,000 simulations)

### Championship Odds — Top 10

| Rank | Team | Seed | Region | Record | AdjEM | Champion % |
|---|---|---|---|---|---|---|
| 1 | **Duke** | #1 | East | 31-3 | +33.3 | **17.2%** |
| 2 | Auburn | #1 | South | 29-4 | +30.6 | 12.9% |
| 3 | Kansas | #1 | West | 28-5 | +27.8 | 9.3% |
| 4 | Alabama | #2 | Midwest | 26-7 | +25.3 | 8.2% |
| 5 | Houston | #1 | Midwest | 30-4 | +30.2 | 8.2% |
| 6 | Florida | #2 | West | 27-5 | +24.5 | 5.9% |
| 7 | Iowa State | #2 | South | 27-6 | +25.7 | 5.6% |
| 8 | Tennessee | #2 | East | 27-6 | +26.4 | 4.9% |
| 9 | Marquette | #3 | Midwest | 25-8 | +22.7 | 3.0% |
| 10 | Wisconsin | #3 | East | 25-8 | +23.7 | 2.6% |

### Consensus Bracket — Final Four

```
East Champion:    (1) Duke
South Champion:   (1) Auburn
Midwest Champion: (1) Houston
West Champion:    (1) Kansas

Final Four:
  Duke    def. Kansas   → Championship
  Auburn  def. Houston  → Championship

National Champion: DUKE
```

---

## CLI Reference

```
python main.py [OPTIONS]

Options:
  -n, --sims INT            Number of simulations (default: 100,000)
  -s, --seed INT            Random seed for reproducibility
  -u, --upset-factor FLOAT  Upset multiplier (1.0=historical, >1=more upsets)
  -c, --compact             Condensed output, skip full odds table
      --portfolio INT       Generate N diversified brackets for office pools
  -t, --team NAME           Detailed stats for a specific team
  -m, --matchup A B         Head-to-head probability breakdown
      --save FILE           Export results to JSON
      --top INT             Teams to show in odds table (default: 20)
      --data FILE           Custom teams data file (default: data/teams.json)
```

### Examples

```bash
# Reproducible 50k-sim run
python main.py --sims 50000 --seed 42

# Bracket competition: generate 10 diversified brackets
python main.py --portfolio 10

# Simulate a more upset-heavy tournament
python main.py --upset-factor 1.5 --compact

# Head-to-head matchup analysis
python main.py --matchup "Duke" "Auburn"

# Deep dive on a Cinderella candidate
python main.py --team "Gonzaga"

# Export to JSON for further analysis
python main.py --save results_2026.json
```

---

## Project Structure

```
Ncaa-sim/
├── main.py              # CLI entry point
├── simulator.py         # Monte Carlo engine & statistics aggregation
├── bracket.py           # Bracket structure, region logic, game simulation
├── models.py            # Win probability models (EM, Pythagorean, historical)
├── report.py            # Terminal output formatting and reporting
├── requirements.txt     # Python dependencies
├── data/
│   └── teams.json       # 2026 tournament field — 68 teams with full stats
└── results_2026.json    # Pre-computed 100k simulation results
```

---

## Updating Team Data

Edit `data/teams.json` to update stats or adjust seedings. Each team entry:

```json
{
  "name": "Duke",
  "abbr": "DUKE",
  "seed": 1,
  "region": "East",
  "conf": "ACC",
  "record": "31-3",
  "wins": 31,
  "losses": 3,
  "adj_o": 123.4,
  "adj_d": 90.1,
  "adj_em": 33.3,
  "adj_t": 68.2,
  "luck": 0.031,
  "sos_adj_em": 11.2,
  "net_ranking": 1,
  "kenpom_rank": 1
}
```

Set `"first_four": true` for First Four participants and list their matchup in `first_four_matchups`.

---

## Dependencies

- **numpy** — random number generation, array operations
- **scipy** — statistical functions
- **pandas** — data handling
- **tabulate** — formatted terminal tables

Install: `pip install -r requirements.txt`
