import sys
import os
import asyncio
import json

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.dirname(base_dir))

try:
    from app.core.database import SessionLocal
    from app.models.schema import PaperBet
    from app.engine.team_analyzer import TeamStatsAnalyzer
except ImportError:
    from backend.app.core.database import SessionLocal
    from backend.app.models.schema import PaperBet
    from backend.app.engine.team_analyzer import TeamStatsAnalyzer

async def backfill():
    db = SessionLocal()
    try:
        single_bets = db.query(PaperBet).filter(PaperBet.is_multiple == False).all()
        print(f"Found {len(single_bets)} single paper bets to inspect...")

        for b in single_bets:
            print(f"Backfilling Bet #{b.id}: {b.match.home_team} vs {b.match.away_team} ({b.market_type} - {b.selection} @ {b.odds})...")
            p = b.prediction
            ev = p.ev_percent if p else 10.0
            model_prob = round(p.model_prob * 100, 1) if p else round((1.0 / (b.odds * 0.9)) * 100, 1)
            fair_odds = p.fair_odds if p else round(100.0 / model_prob, 2)

            dossier = await TeamStatsAnalyzer.fetch_team_dossier(
                home_team=b.match.home_team,
                away_team=b.match.away_team,
                league=b.match.league,
                lam=1.45,
                mu=1.25,
                market=b.market_type,
                selection=b.selection,
                odds=b.odds,
                ev_percent=ev
            )

            if dossier and "dixon_coles" in dossier:
                dossier["dixon_coles"]["model_prob"] = model_prob
                dossier["dixon_coles"]["fair_odds"] = fair_odds
                dossier["dixon_coles"]["kelly_stake_percent"] = round((b.stake / 1000.0) * 100, 1)

            b.stats_analysis = json.dumps(dossier, ensure_ascii=False)
            db.commit()
            print(f"   ✓ Bet #{b.id} stats analysis successfully persisted!")

        print("\nAll single paper bets backfilled successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(backfill())
