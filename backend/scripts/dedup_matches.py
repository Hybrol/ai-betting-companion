import sys
import os
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.dirname(base_dir))

try:
    from app.core.database import SessionLocal
    from app.engine.normalizer import create_match_key, normalize_team_name, normalize_league_name
    from app.models.schema import Match, BookmakerOdds, Prediction, PaperBet
except ImportError:
    from backend.app.core.database import SessionLocal
    from backend.app.engine.normalizer import create_match_key, normalize_team_name, normalize_league_name
    from backend.app.models.schema import Match, BookmakerOdds, Prediction, PaperBet
from collections import defaultdict

def run_dedup():
    db = SessionLocal()
    try:
        all_matches = db.query(Match).all()
        by_canon_key = defaultdict(list)

        for m in all_matches:
            c_key = create_match_key(m.home_team, m.away_team, m.kickoff.isoformat())
            by_canon_key[c_key].append(m)

        merged_groups = 0
        deleted_count = 0

        for c_key, group in by_canon_key.items():
            if len(group) <= 1:
                m = group[0]
                m.match_key = c_key
                m.home_team = normalize_team_name(m.home_team)
                m.away_team = normalize_team_name(m.away_team)
                m.league = normalize_league_name(m.league)
                continue

            merged_groups += 1
            def sort_key(m_item):
                pb_count = db.query(PaperBet).filter(PaperBet.match_id == m_item.id).count()
                has_exact_key = 1 if m_item.match_key == c_key else 0
                odds_count = db.query(BookmakerOdds).filter(BookmakerOdds.match_id == m_item.id).count()
                return (pb_count, has_exact_key, odds_count, m_item.id)

            group.sort(key=sort_key, reverse=True)
            primary = group[0]
            duplicates = group[1:]

            print(f"[GROUP] Merging {len(duplicates)} duplicates into Primary #{primary.id} ({primary.home_team} vs {primary.away_team} - {primary.league})")

            for dup in duplicates:
                print(f"   -> Merging #{dup.id} ({dup.home_team} vs {dup.away_team} - {dup.league})")
                # Free unique constraint on match_key immediately
                dup.match_key = f"dup_{dup.id}_{c_key}"
                db.flush()

                # Reassign paper bets
                db.query(PaperBet).filter(PaperBet.match_id == dup.id).update({"match_id": primary.id})

                # Merge odds
                dup_odds = db.query(BookmakerOdds).filter(BookmakerOdds.match_id == dup.id).all()
                for d_odd in dup_odds:
                    exists = db.query(BookmakerOdds).filter(
                        BookmakerOdds.match_id == primary.id,
                        BookmakerOdds.bookmaker == d_odd.bookmaker,
                        BookmakerOdds.market_type == d_odd.market_type,
                        BookmakerOdds.selection == d_odd.selection
                    ).first()
                    if exists:
                        if d_odd.odds > exists.odds:
                            exists.odds = d_odd.odds
                        db.delete(d_odd)
                    else:
                        d_odd.match_id = primary.id

                # Delete duplicate predictions
                db.query(Prediction).filter(Prediction.match_id == dup.id).delete()
                db.delete(dup)
                db.flush()
                deleted_count += 1

            primary.match_key = c_key
            primary.home_team = normalize_team_name(primary.home_team)
            primary.away_team = normalize_team_name(primary.away_team)
            primary.league = normalize_league_name(primary.league)
            db.flush()

        db.commit()
        print(f"\n[DONE] Successfully merged {merged_groups} duplicate match groups and removed {deleted_count} duplicate match rows.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Deduplication failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_dedup()
