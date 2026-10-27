import logging
import asyncio
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..core.database import SessionLocal
from ..models.schema import Match, PaperBet, BetStatus, MatchStatus
from ..engine.paper_trader import PaperTrader
from ..engine.discord_notifier import DiscordNotifier
from ..engine.normalizer import clean_string

logger = logging.getLogger(__name__)

# Mapping from canonical leagues in our DB to ESPN's public scoreboard slugs
ESPN_LEAGUE_MAP = {
    # Portugal
    "liga portugal": "por.1",
    "liga portugal betclic": "por.1",
    "portugal": "por.1",
    "portugal - primeira liga": "por.1",
    # Spain
    "la liga": "esp.1",
    "espanha - la liga": "esp.1",
    # England
    "premier league": "eng.1",
    "inglaterra - premier league": "eng.1",
    # Italy
    "serie a": "ita.1",
    "itália - serie a": "ita.1",
    # Germany
    "bundesliga": "ger.1",
    "alemanha - bundesliga": "ger.1",
    # France
    "ligue 1": "fra.1",
    "frança - ligue 1": "fra.1",
    # European
    "champions league": "uefa.champions",
    "europa league": "uefa.europa",
    "conference league": "uefa.europa.conf",
    # Brazil
    "brasileirão": "bra.1",
    "brasileirao": "bra.1",
    "brazil serie a": "bra.1",
    "brasil - serie a": "bra.1",
    "brasil - série a": "bra.1",
    # Arab Leagues
    "saudi pro league": "sau.1",
    "uae pro league": "uae.1",
    "qatar stars league": "qat.1",
}

class LiveScoreResolver:
    @staticmethod
    def _match_teams(name1: str, name2: str) -> bool:
        c1, c2 = clean_string(name1), clean_string(name2)
        if c1 == c2:
            return True
        if c1 and c2 and (c1 in c2 or c2 in c1):
            return True
        from difflib import SequenceMatcher
        return SequenceMatcher(None, c1, c2).ratio() >= 0.60

    @classmethod
    async def fetch_espn_scoreboard(cls, league_slug: str) -> list[dict]:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/scoreboard"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("events", [])
        except Exception as e:
            logger.debug(f"[LIVE SCORES] Failed to fetch ESPN scoreboard for {league_slug}: {e}")
        return []

    @classmethod
    async def check_and_resolve_live_matches(cls) -> int:
        """
        Runs every 60 seconds:
        1. Identifies matches that have active PENDING paper bets or are active today.
        2. Fetches live scores from ESPN's public scoreboard.
        3. Updates in-play scores (home_score, away_score, status = IN_PLAY).
        4. When a match is completed:
           - Automatically resolves all paper bets (GREEN / RED).
           - Updates user bankroll, total PnL, greens/reds.
           - Sends rich Discord webhook notification celebrating the win or logging the result.
        Returns the number of bets newly settled.
        """
        db: Session = SessionLocal()
        total_settled = 0
        try:
            now_utc = datetime.utcnow()
            cutoff_past = now_utc - timedelta(hours=36)
            cutoff_future = now_utc + timedelta(hours=24)

            # Matches with PENDING paper bets OR currently LIVE matches (even across midnight!)
            # OR scheduled matches within the last 36h / next 24h
            pending_subquery = db.query(PaperBet.match_id).filter(
                PaperBet.status == BetStatus.PENDING
            ).distinct().all()
            pending_ids = [m[0] for m in pending_subquery]

            active_matches = db.query(Match).filter(
                (Match.id.in_(pending_ids)) |
                (Match.status == MatchStatus.LIVE) |
                (
                    (Match.kickoff >= cutoff_past) &
                    (Match.kickoff <= cutoff_future) &
                    (Match.status == MatchStatus.SCHEDULED)
                )
            ).all()

            if not active_matches:
                return 0

            # Group matches by required ESPN league slug
            leagues_to_fetch = set()
            for m in active_matches:
                norm_lg = m.league.lower().strip()
                slug = ESPN_LEAGUE_MAP.get(norm_lg)
                if slug:
                    leagues_to_fetch.add(slug)
                h_low, a_low = m.home_team.lower(), m.away_team.lower()
                if any(x in h_low or x in a_low for x in ["flamengo", "coritiba", "gremio", "atletico", "palmeiras", "sao paulo"]):
                    leagues_to_fetch.add("bra.1")

            # Always ensure primary active leagues are tracked
            leagues_to_fetch.update(["por.1", "esp.1", "fra.1", "bra.1"])

            # Fetch scoreboards concurrently
            tasks = [cls.fetch_espn_scoreboard(slug) for slug in leagues_to_fetch]
            scoreboards = await asyncio.gather(*tasks, return_exceptions=True)

            all_espn_events = []
            for sb in scoreboards:
                if isinstance(sb, list):
                    all_espn_events.extend(sb)

            for match in active_matches:
                for ev in all_espn_events:
                    comps = ev.get("competitions", [])
                    if not comps:
                        continue
                    comp = comps[0]
                    competitors = comp.get("competitors", [])
                    home_comp = next((c for c in competitors if c.get("homeAway") == "home"), None)
                    away_comp = next((c for c in competitors if c.get("homeAway") == "away"), None)

                    if not home_comp or not away_comp:
                        continue

                    h_name = home_comp.get("team", {}).get("displayName") or home_comp.get("team", {}).get("name", "")
                    a_name = away_comp.get("team", {}).get("displayName") or away_comp.get("team", {}).get("name", "")

                    if cls._match_teams(h_name, match.home_team) and cls._match_teams(a_name, match.away_team):
                        h_score_raw = home_comp.get("score")
                        a_score_raw = away_comp.get("score")

                        h_score = int(h_score_raw) if h_score_raw is not None and str(h_score_raw).isdigit() else match.home_score
                        a_score = int(a_score_raw) if a_score_raw is not None and str(a_score_raw).isdigit() else match.away_score

                        status_info = comp.get("status", {})
                        is_completed = status_info.get("type", {}).get("completed", False)
                        state = status_info.get("type", {}).get("state", "pre")
                        clock_desc = status_info.get("displayClock") or status_info.get("type", {}).get("description", "")

                        if h_score is not None and a_score is not None:
                            match.home_score = h_score
                            match.away_score = a_score

                        if is_completed:
                            if match.status != MatchStatus.FINISHED:
                                logger.info(
                                    f"[LIVE RESOLVER] Match FINISHED: {match.home_team} {h_score} - {a_score} {match.away_team}. Auto-resolving bets!"
                                )
                                match.status = MatchStatus.FINISHED
                                db.commit()

                                # Auto-resolve paper bets!
                                resolved_bets = PaperTrader.resolve_match_bets(
                                    db=db,
                                    match_id=match.id,
                                    home_score=h_score,
                                    away_score=a_score
                                )
                                total_settled += len(resolved_bets)

                                # Send Discord alerts for each resolved bet
                                br = PaperTrader.get_or_create_bankroll(db)
                                for b in resolved_bets:
                                    is_green = (b.status == BetStatus.GREEN)
                                    await DiscordNotifier.notify_bet_result(
                                        home_team=match.home_team,
                                        away_team=match.away_team,
                                        league=match.league,
                                        home_score=h_score,
                                        away_score=a_score,
                                        market_type=b.market_type,
                                        selection=b.selection,
                                        bookmaker=b.bookmaker,
                                        odds=b.odds,
                                        stake=b.stake,
                                        profit_loss=b.profit_loss,
                                        is_green=is_green,
                                        current_balance=br.current_balance
                                    )
                        elif state == "in":
                            if match.status != MatchStatus.LIVE:
                                match.status = MatchStatus.LIVE
                                logger.info(
                                    f"[LIVE RESOLVER] Match LIVE ({clock_desc}): {match.home_team} {h_score} - {a_score} {match.away_team}"
                                )
                            db.commit()

                            # Check for early mathematically definitive settlements (e.g. BTTS 1-1, Over crossed)
                            early_resolved = PaperTrader.check_early_in_play_settlement(
                                db=db,
                                match_id=match.id,
                                home_score=h_score,
                                away_score=a_score
                            )
                            if early_resolved:
                                total_settled += len(early_resolved)
                                br = PaperTrader.get_or_create_bankroll(db)
                                for b in early_resolved:
                                    is_green = (b.status == BetStatus.GREEN)
                                    logger.info(
                                        f"[LIVE RESOLVER] Early settlement for {match.home_team} vs {match.away_team}: "
                                        f"{b.market_type} {b.selection} -> {'GREEN' if is_green else 'RED'}!"
                                    )
                                    await DiscordNotifier.notify_bet_result(
                                        home_team=match.home_team,
                                        away_team=match.away_team,
                                        league=match.league,
                                        home_score=h_score,
                                        away_score=a_score,
                                        market_type=b.market_type,
                                        selection=b.selection,
                                        bookmaker=b.bookmaker,
                                        odds=b.odds,
                                        stake=b.stake,
                                        profit_loss=b.profit_loss,
                                        is_green=is_green,
                                        current_balance=br.current_balance
                                    )
                        break
        except Exception as e:
            logger.error(f"[LIVE RESOLVER ERROR] {e}", exc_info=True)
        finally:
            db.close()

        return total_settled
