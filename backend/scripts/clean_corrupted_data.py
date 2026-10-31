import sys
import os
import sqlite3

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
sys.path.insert(0, os.path.dirname(base_dir))

def ensure_columns(db_file):
    if not os.path.exists(db_file):
        return
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if "paper_bets" in tables:
        cols = [col[1] for col in c.execute("PRAGMA table_info(paper_bets)").fetchall()]
        for col_name, col_type in [("is_multiple", "BOOLEAN DEFAULT 0"), ("multiple_legs", "TEXT"), ("stats_analysis", "TEXT"), ("confidence", "VARCHAR(32) DEFAULT 'MÉDIA'"), ("reasoning", "TEXT")]:
            if col_name not in cols:
                c.execute(f"ALTER TABLE paper_bets ADD COLUMN {col_name} {col_type}")
    conn.commit()
    conn.close()

db_local = os.path.join(base_dir, "data", "betting_companion.db")
ensure_columns(db_local)

try:
    from app.core.database import SessionLocal
    from app.models.schema import Match, BookmakerOdds, Prediction, PaperBet, Bankroll, BankrollHistory, BetStatus
    from app.engine.normalizer import normalize_team_name, normalize_league_name, create_match_key
except ImportError:
    from backend.app.core.database import SessionLocal
    from backend.app.models.schema import Match, BookmakerOdds, Prediction, PaperBet, Bankroll, BankrollHistory, BetStatus
    from backend.app.engine.normalizer import normalize_team_name, normalize_league_name, create_match_key

PORTUGUESE_TEAMS = {
    "SL Benfica", "Sporting CP", "FC Porto", "SC Braga", "Vitória SC",
    "Santa Clara", "FC Famalicão", "Moreirense FC", "Casa Pia AC", "Rio Ave FC",
    "Gil Vicente FC", "GD Estoril Praia", "FC Arouca", "Boavista FC",
    "AVS Futebol SAD", "CF Estrela Amadora", "CD Nacional", "SC Farense"
}

ENGLISH_TEAMS = {
    "Arsenal", "Aston Villa", "AFC Bournemouth", "Brentford", "Brighton",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Ipswich Town",
    "Leicester City", "Liverpool", "Manchester City", "Manchester United",
    "Newcastle United", "Nottingham Forest", "Southampton", "Tottenham Hotspur",
    "West Ham United", "Wolverhampton Wanderers"
}

BRAZILIAN_TEAMS = {
    "Flamengo", "Palmeiras", "São Paulo", "Corinthians", "Fluminense",
    "Botafogo", "Grêmio", "Internacional", "Atlético Mineiro", "Athletico Paranaense",
    "Cruzeiro", "Vasco da Gama", "Fortaleza EC", "EC Bahia", "Cuiabá", "Coritiba", "Santos FC"
}

def is_corrupted_match(m: Match) -> tuple[bool, str]:
    h = m.home_team
    a = m.away_team
    lg = m.league

    if h == a:
        return True, f"Identical teams: {h} vs {a}"

    if (h in BRAZILIAN_TEAMS or a in BRAZILIAN_TEAMS) and lg in {"Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1", "Liga Portugal", "Champions League", "Europa League", "Conference League"}:
        return True, f"Brazilian team in European competition: {h} vs {a} ({lg})"

    if lg in {"Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"}:
        if h in PORTUGUESE_TEAMS or a in PORTUGUESE_TEAMS:
            return True, f"Portuguese club in {lg}: {h} vs {a}"

    if lg in {"La Liga", "Serie A", "Bundesliga", "Ligue 1", "Liga Portugal"}:
        if h in ENGLISH_TEAMS or a in ENGLISH_TEAMS:
            return True, f"English club in {lg}: {h} vs {a}"

    if (h == "FC Barcelona" and "Estoril" in a) or (a == "FC Barcelona" and "Estoril" in h):
        return True, "FC Barcelona vs GD Estoril Praia phantom match"
    if ("Manchester City" in (h, a) and "Sporting CP" in (h, a) and lg == "Premier League"):
        return True, "Manchester City vs Sporting CP in Premier League"
    if ("Estoril" in h or "Estoril" in a) and "Le Mans" in (h, a):
        return True, "GD Estoril Praia vs Le Mans in Ligue 1"

    return False, ""

def clean_database():
    db = SessionLocal()
    try:
        bankroll = db.query(Bankroll).first()
        all_matches = db.query(Match).all()
        print(f"Inspecting {len(all_matches)} total matches in database...")

        corrupted_matches = []
        for m in all_matches:
            is_bad, reason = is_corrupted_match(m)
            if is_bad:
                corrupted_matches.append((m, reason))

        print(f"Found {len(corrupted_matches)} corrupted phantom matches to remove.")

        removed_bets = 0
        for m, reason in corrupted_matches:
            print(f"[-] Deleting #{m.id}: {m.home_team} vs {m.away_team} ({m.league}) -> {reason}")

            bets = db.query(PaperBet).filter(PaperBet.match_id == m.id).all()
            for b in bets:
                removed_bets += 1
                if b.status == BetStatus.GREEN:
                    if bankroll:
                        bankroll.greens = max(0, bankroll.greens - 1)
                        bankroll.total_pnl -= b.profit_loss
                        bankroll.current_balance -= (b.stake + b.profit_loss)
                elif b.status == BetStatus.RED:
                    if bankroll:
                        bankroll.reds = max(0, bankroll.reds - 1)
                        bankroll.total_pnl += b.stake
                        bankroll.current_balance += b.stake
                elif b.status == BetStatus.PENDING:
                    if bankroll:
                        bankroll.current_balance += b.stake

                if bankroll:
                    bankroll.total_bets = max(0, bankroll.total_bets - 1)
                    bankroll.total_staked = max(0.0, bankroll.total_staked - b.stake)

                db.delete(b)

            db.query(BookmakerOdds).filter(BookmakerOdds.match_id == m.id).delete()
            db.query(Prediction).filter(Prediction.match_id == m.id).delete()
            db.delete(m)

        db.commit()
        print(f"Removed {len(corrupted_matches)} phantom matches and {removed_bets} associated bets.")

        # Re-normalize remaining matches and merge duplicates safely
        remaining = db.query(Match).all()
        renamed = 0
        merged = 0

        for m in remaining:
            new_h = normalize_team_name(m.home_team)
            new_a = normalize_team_name(m.away_team)
            new_lg = normalize_league_name(m.league)
            new_key = create_match_key(new_h, new_a, m.kickoff.isoformat())

            # Check if another match already has this target key
            duplicate = db.query(Match).filter(Match.match_key == new_key, Match.id != m.id).first()
            if duplicate:
                merged += 1
                db.query(BookmakerOdds).filter(BookmakerOdds.match_id == m.id).update({"match_id": duplicate.id})
                db.query(Prediction).filter(Prediction.match_id == m.id).update({"match_id": duplicate.id})
                db.query(PaperBet).filter(PaperBet.match_id == m.id).update({"match_id": duplicate.id})
                db.delete(m)
                db.flush()
            else:
                if new_h != m.home_team or new_a != m.away_team or new_lg != m.league or new_key != m.match_key:
                    renamed += 1
                    m.home_team = new_h
                    m.away_team = new_a
                    m.league = new_lg
                    m.match_key = new_key
                    db.flush()

        db.commit()
        print(f"Normalized {renamed} matches and merged {merged} duplicates.")

        if bankroll:
            print(f"Bankroll updated: {bankroll.current_balance:.2f} EUR (PnL: {bankroll.total_pnl:.2f} EUR, Greens: {bankroll.greens}, Reds: {bankroll.reds})")

    finally:
        db.close()

if __name__ == "__main__":
    clean_database()
