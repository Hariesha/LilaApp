# INSIGHTS.md

Three data-backed insights from analyzing 89,104 events across 796 matches (Feb 10–14, 2026).

---

## Insight 1 — Human PvP is almost nonexistent; bots dominate kills

### What caught my eye

The kill event breakdown is striking:

| Event | Count |
|---|---|
| `Kill` (human kills human) | **3** |
| `Killed` (human killed by human) | **3** |
| `BotKill` (human kills bot) | **2,415** |
| `BotKilled` (human killed by bot) | **700** |

Across 796 matches and 339 unique human players, there were only **3 human-vs-human kills** in 5 days of production data. Players engage with bots ~800× more than with each other.

### What the data shows

- Ratio of BotKill : Kill = **805:1**
- 339 human players, 796 matches, and near-zero PvP interaction
- Human players die to bots more than they kill them (700 BotKilled vs 2,415 BotKill is a ~3.4:1 kill-to-death ratio against bots — respectable, but suggests bots are a real threat)

### Actionable items

- **Is the human encounter rate intentional?** If LILA BLACK is designed as a PvE extraction shooter, this is expected. If PvP tension is a design goal, spawn density and match size need revisiting — players may not be crossing paths.
- **Metrics to track:** Average human-to-human encounters per match, distance between human spawn points, match completion rate (extract vs die to bot).
- **Level Designer action:** Use the heatmap (Kill/BotKill overlay) to check whether kills cluster in specific zones (choke points, loot hot spots) or are spread randomly. If bot kills are spread uniformly and human kills are zero, map routing may be too sprawling — consider funnel zones that force paths to converge.

### Why a level designer should care

If maps never create human player encounters, the extraction game loop loses tension. Routing design (corridors, objective placement, extract points) directly controls how often players cross paths.

---

## Insight 2 — AmbroseValley captures 69% of all play; GrandRift is underutilized

### What caught my eye

| Map | Event rows | Share |
|---|---|---|
| AmbroseValley | 61,013 | **68.6%** |
| Lockdown | 21,238 | **23.8%** |
| GrandRift | 6,853 | **7.7%** |

GrandRift has less than 1-in-13 events despite being one of three live maps.

### What the data shows

- AmbroseValley has ~8.9× more events than GrandRift
- Lockdown (close-quarters) is second despite presumably being a niche map
- GrandRift's low representation could mean: fewer matches played there, shorter matches, or earlier truncation of data collection

### Actionable items

- **Investigate the rotation queue:** If maps are randomly rotated, 7.7% is significantly below the expected ~33%. Check matchmaking logs to confirm whether GrandRift is being selected at low frequency by the rotation system or by player preference.
- **Metrics to track:** Avg match duration per map, early exit rate per map, player retention across maps.
- **Level Designer action:** Analyse GrandRift specifically — use the heatmap on Lockdown vs GrandRift to compare loot density and kill-zone concentration. If GrandRift has dead zones (no traffic, no kills), the layout may be too large or too empty to generate tension in the match timeframe.

### Why a level designer should care

A map that receives 7.7% of play cannot provide sufficient feedback loops for iteration. If GrandRift is deprioritized in the rotation or abandoned by players, the team is shipping and maintaining a map that isn't contributing to the core engagement loop.

---

## Insight 3 — Players rarely die to the storm; they die to bots or extract first

### What caught my eye

| Death type | Count |
|---|---|
| `KilledByStorm` | **39** |
| `BotKilled` (killed by a bot) | **700** |
| `Killed` (killed by human) | **3** |

The storm — the map's primary time-pressure mechanic — accounts for only **5.3%** of all deaths. Bots are responsible for **94.5%** of player deaths.

### What the data shows

- Across 89k events and 796 matches, the storm killed just 39 players total (~0.049 per match on average)
- This is extremely low for a mechanic that is supposed to be a core driver of pacing and urgency
- Likely interpretation: either players extract before the storm reaches them, or the storm's movement speed and size make it easily avoidable

### Actionable items

- **Test storm pressure:** If the storm is the core risk mechanic but isn't killing players, it may not be creating urgency. The storm could move faster, shrink more aggressively, or deal damage in a wider radius.
- **Metrics to track:** Time-to-storm-death per match, % of matches where at least one player dies to storm, average distance from storm boundary at time of extract.
- **Level Designer action:** Using the timeline playback, watch matches where KilledByStorm events occur — identify whether they happen at the start of the storm or near the end. If late, the storm is providing a clean sweep mechanic rather than a real pressure tool mid-match. Shrink the extractable safe zone and re-test.
- **Note opportunity:** Storm deaths clustering in specific map regions could reveal design flaws — dead-end corridors or loot zones that trap players in the storm path. Use the KilledByStorm heatmap to locate those.

### Why a level designer should care

The storm (shrinking zone) is the signature mechanic of battle-royale and extraction games — it creates urgency, forces movement, and drives player encounters. If it has near-zero impact on outcomes, one of the game's core engagement levers is effectively broken.
