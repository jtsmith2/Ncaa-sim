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

## Office Pool Portfolio Mode

If your pool allows multiple bracket submissions, `--portfolio N` generates N brackets designed to **maximize collective coverage** rather than just repeating the single most likely outcome.

### Why not just submit the same bracket N times?

Submitting 10 identical "Duke wins" brackets gives you no advantage — you're competing against everyone else who also picked Duke. Portfolio mode spreads your brackets across different scenarios so you're covered when the inevitable upsets happen.

### How the portfolio algorithm works

**Step 1 — Proportional champion allocation** using the [largest-remainder method](https://en.wikipedia.org/wiki/Largest_remainder_method): champions are assigned bracket slots in proportion to their championship probability. More likely champions get more slots, but every significant contender gets at least one.

**Step 2 — Runner-up diversification**: The NCAA bracket structure means the championship game is always an `East/West region winner vs. South/Midwest region winner`. For every bracket, the algorithm also forces a *different* runner-up from the opposite half — so even if two brackets both have Duke winning, they each predict a different championship game opponent. All N brackets end up with **unique championship matchups**.

**Step 3 — Conditional picks**: Every other game in the bracket picks the highest-probability winner *given* the assigned champion and finalist. If Iowa State is forced to win, the bracket still correctly picks Auburn to reach the Final Four — because the upset is Iowa State *beating* Auburn there, not Auburn failing to make it.

### Example — 10 brackets

| # | Champion | Champ% | Title Game vs | Unique? |
|---|---|---|---|---|
| 1 | Duke | 17.2% | Auburn | ✓ |
| 2 | Duke | 17.2% | Alabama | ✓ different matchup |
| 3 | Auburn | 13.0% | Duke | ✓ |
| 4 | Auburn | 13.0% | Kansas | ✓ different matchup |
| 5 | Kansas | 9.3% | Auburn | ✓ |
| 6 | Alabama | 8.3% | Duke | ✓ |
| 7 | Houston | 8.1% | Duke | ✓ |
| 8 | Florida | 5.8% | Auburn | ✓ |
| 9 | Iowa State | 5.7% | Duke | ✓ |
| 10 | Tennessee | 5.0% | Auburn | ✓ |

**Combined champion probability: 72.3%** — meaning there's a ~72% chance at least one of your 10 champions is correct.

```bash
python main.py --portfolio 10
python main.py --portfolio 10 --save my_brackets.json
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
  -p, --portfolio INT       Generate N diversified brackets for office pools
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

# Office pool: generate 10 diversified brackets
python main.py --portfolio 10

# Office pool: generate and save to JSON
python main.py --portfolio 10 --save my_brackets.json

# Simulate a more upset-heavy tournament
python main.py --upset-factor 1.5 --compact

# Head-to-head matchup analysis
python main.py --matchup "Duke" "Auburn"

# Deep dive on a Cinderella candidate
python main.py --team "Gonzaga"

# Export full simulation results to JSON
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
