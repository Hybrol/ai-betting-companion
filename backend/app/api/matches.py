from datetime import datetime
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models.schema import Match, BookmakerOdds, Prediction, MatchStatus
from ..engine.normalizer import create_match_key
from ..engine.predictor import MatchPredictor
from ..engine.value_finder import ValueFinder
from ..engine.paper_trader import PaperTrader
from ..scrapers.betclic import BetclicScraper
from ..scrapers.betano import BetanoScraper
from ..scrapers.solverde import SolverdeScraper

router = APIRouter(prefix="/matches", tags=["Matches"])

async def run_sync_task(db: Session, target_league: str | None = None):
    scrapers = [BetclicScraper(), BetanoScraper(), SolverdeScraper()]
    leagues = [target_league] if target_league else [
        "Liga Portugal", "Premier League", "La Liga", "Serie A", "Bundesliga", "Champions League"
    ]

    br = PaperTrader.get_or_create_bankroll(db)
    current_bankroll = br.current_balance

    for league in leagues:
        all_scraped = []
        for scraper in scrapers:
            try:
                matches = await scraper.fetch_league_matches(league)
                all_scraped.extend(matches)
            except Exception as e:
                print(f"Scraper {scraper.bookmaker_name} failed on {league}: {e}")

        # Group by match key
        for sm in all_scraped:
            m_key = create_match_key(sm.home_team, sm.away_team, sm.kickoff.isoformat())
            match = db.query(Match).filter(Match.match_key == m_key).first()

            if not match:
                match = Match(
                    match_key=m_key,
                    home_team=sm.home_team,
                    away_team=sm.away_team,
                    league=league,
                    kickoff=sm.kickoff,
                    status=MatchStatus.SCHEDULED
                )
                db.add(match)
                db.flush()

            # Store / update bookmaker odds
            for odd_item in sm.odds:
                existing_odd = db.query(BookmakerOdds).filter(
                    BookmakerOdds.match_id == match.id,
                    BookmakerOdds.bookmaker == sm.bookmaker,
                    BookmakerOdds.market_type == odd_item.market_type,
                    BookmakerOdds.selection == odd_item.selection
                ).first()

                if existing_odd:
                    existing_odd.odds = odd_item.odds
                    existing_odd.timestamp = datetime.utcnow()
                else:
                    new_odd = BookmakerOdds(
                        match_id=match.id,
                        bookmaker=sm.bookmaker,
                        market_type=odd_item.market_type,
                        selection=odd_item.selection,
                        odds=odd_item.odds
                    )
                    db.add(new_odd)

            db.commit()

            # Run value detection for this match
            # Gather all 1X2 odds
            all_odds = db.query(BookmakerOdds).filter(
                BookmakerOdds.match_id == match.id,
                BookmakerOdds.market_type == "1X2"
            ).all()

            odds_by_sel: dict[str, list[tuple[str, float]]] = {"1": [], "X": [], "2": []}
            bookmaker_sets: dict[str, dict[str, float]] = {}
            for o in all_odds:
                odds_by_sel.setdefault(o.selection, []).append((o.bookmaker, o.odds))
                bookmaker_sets.setdefault(o.bookmaker, {})[o.selection] = o.odds

            multi_1x2 = [
                [b_odds.get("1", 0), b_odds.get("X", 0), b_odds.get("2", 0)]
                for b_odds in bookmaker_sets.values()
                if "1" in b_odds and "X" in b_odds and "2" in b_odds
            ]

            probs = MatchPredictor.estimate_probabilities(
                league, match.home_team, match.away_team, multi_1x2
            )

            # Find values
            values = ValueFinder.scan_for_value(
                match.id, match.home_team, match.away_team, match.league,
                odds_by_sel, probs, current_bankroll
            )

            # Update prediction records
            # Clear old predictions for this match
            db.query(Prediction).filter(Prediction.match_id == match.id).delete()
            for v in values:
                p = Prediction(
                    match_id=match.id,
                    market_type=v.market_type,
                    selection=v.selection,
                    model_prob=v.model_prob,
                    fair_odds=v.fair_odds,
                    best_bookmaker=v.best_bookmaker,
                    best_odds=v.best_odds,
                    ev_percent=v.ev_percent,
                    kelly_stake_percent=v.kelly_stake_percent,
                    recommended_stake=v.recommended_stake
                )
                db.add(p)

            db.commit()

@router.get("/")
def list_matches(
    league: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Match)
    if league:
        query = query.filter(Match.league == league)
    if status:
        query = query.filter(Match.status == status)

    matches = query.order_by(Match.kickoff.asc()).all()

    result = []
    for m in matches:
        odds_list = []
        for o in m.odds:
            odds_list.append({
                "bookmaker": o.bookmaker,
                "market_type": o.market_type,
                "selection": o.selection,
                "odds": o.odds
            })

        preds_list = []
        for p in m.predictions:
            preds_list.append({
                "id": p.id,
                "selection": p.selection,
                "model_prob": p.model_prob,
                "fair_odds": p.fair_odds,
                "best_bookmaker": p.best_bookmaker,
                "best_odds": p.best_odds,
                "ev_percent": p.ev_percent,
                "recommended_stake": p.recommended_stake
            })

        result.append({
            "id": m.id,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "league": m.league,
            "kickoff": m.kickoff.isoformat(),
            "status": m.status.value,
            "home_score": m.home_score,
            "away_score": m.away_score,
            "odds": odds_list,
            "predictions": preds_list
        })

    return result

@router.post("/sync")
async def trigger_sync(
    league: str | None = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Triggers an on-demand scrape and value analysis for Portuguese sportsbooks.
    """
    await run_sync_task(db, league)
    return {"message": "Sync complete", "league": league or "All Leagues"}
