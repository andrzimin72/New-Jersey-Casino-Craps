# New-Jersey-Casino-Craps
This is the complete, fully integrated, and single-file Python script that implements a New Jersey Casino Craps game with all requested features:
- multi-player support (2-8 players);
- shooter rotation after 7-out;
- odds Bets (true odds on Pass/Come);
- place Bets (4,5,6,8,9,10) with correct New Jersey payouts;
- buy Bets (true odds + 5% vig);
- lay Bets (true odds + 5% vig);
- fire Bet (24:1 / 249:1 / 999:1 for 4/5/6 unique points);
- procedural dice & table graphics (no external images);
- dice roll animation;
- bet buttons that highlight when clicked;
- comprehensive audit logging;
- export logs to CSV.

The theoretical RTP of a properly implemented Craps game depends entirely on the types of bets players make. May be Craps is unique in that different bets have wildly different house edges, so the overall RTP is player-determined, not game-determined. I suppose this is a high-RTP game - if players stick to Pass + full Odds, RTP can exceed 99% (e.g., 10× odds - RTP ≈ 99.4%). The Fire Bet is the only truly "slot-like" low-RTP feature - which is acceptable, as it’s optional and clearly high-risk.

I think this game’s effective RTP ranges from ~75% (Fire Bet only) to >99% (Pass + max Odds) - which is excellent and authentic to real-world New Jersey craps.

How to Run: python3 New_Jersey_Casino_Craps.py

Output Files:
- craps_audit.log - real-time regulatory-compliant log;
- craps_audit.csv - exported on demand.

This game is fully compliant with the New Jersey Casino regulations. I suppose it’s quite possible to exploit this program as methodical guide for studying of some disciplines «Probability Theory», «Game Theory», «Analytic Combinatorics», «Analysis Algorithms» and «Risk Management». May be this script will help to master the game from scratch in a week and make the learning process fun and exciting. Though we shouldn’t forget the game of real Craps is associated with financial risks, as the result depends on a random event - the number on which the player has bet.

