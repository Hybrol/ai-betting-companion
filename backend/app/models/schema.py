import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from ..core.database import Base

class BetStatus(str, enum.Enum):
    PENDING = "PENDING"
    GREEN = "GREEN"   # Won
    RED = "RED"       # Lost
    VOID = "VOID"     # Returned / Cancelled

class MatchStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    match_key = Column(String(128), unique=True, index=True, nullable=False) # e.g. santa_clara_vs_sl_benfica_20261026
    home_team = Column(String(100), nullable=False, index=True)
    away_team = Column(String(100), nullable=False, index=True)
    league = Column(String(64), nullable=False, index=True)
    kickoff = Column(DateTime, nullable=False, index=True)
    status = Column(Enum(MatchStatus), default=MatchStatus.SCHEDULED, nullable=False)
    
    # Results
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    odds = relationship("BookmakerOdds", back_populates="match", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="match", cascade="all, delete-orphan")
    bets = relationship("PaperBet", back_populates="match", cascade="all, delete-orphan")

class BookmakerOdds(Base):
    __tablename__ = "bookmaker_odds"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    bookmaker = Column(String(32), nullable=False, index=True) # "Betclic", "Betano", "Solverde"
    
    market_type = Column(String(32), nullable=False) # "1X2", "OVER_UNDER_2_5", "BTTS"
    selection = Column(String(32), nullable=False)   # "1", "X", "2", "OVER", "UNDER", "YES", "NO"
    odds = Column(Float, nullable=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="odds")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    market_type = Column(String(32), nullable=False)
    selection = Column(String(32), nullable=False)
    
    # Probabilistic engine
    model_prob = Column(Float, nullable=False)     # e.g. 0.78 (78%)
    fair_odds = Column(Float, nullable=False)      # e.g. 1.28
    best_bookmaker = Column(String(32), nullable=False)
    best_odds = Column(Float, nullable=False)      # e.g. 1.35
    
    ev_percent = Column(Float, nullable=False)     # e.g. +5.4%
    kelly_stake_percent = Column(Float, nullable=False) # recommended stake %
    recommended_stake = Column(Float, nullable=False)   # recommended stake in EUR
    
    created_at = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="predictions")
    bets = relationship("PaperBet", back_populates="prediction")

class PaperBet(Base):
    __tablename__ = "paper_bets"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    
    bookmaker = Column(String(32), nullable=False)
    market_type = Column(String(32), nullable=False)
    selection = Column(String(32), nullable=False)
    
    odds = Column(Float, nullable=False)
    stake = Column(Float, nullable=False)
    potential_payout = Column(Float, nullable=False)
    
    status = Column(Enum(BetStatus), default=BetStatus.PENDING, nullable=False, index=True)
    payout = Column(Float, default=0.0)
    profit_loss = Column(Float, default=0.0)
    
    placed_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    match = relationship("Match", back_populates="bets")
    prediction = relationship("Prediction", back_populates="bets")

class Bankroll(Base):
    __tablename__ = "bankroll"

    id = Column(Integer, primary_key=True, index=True)
    current_balance = Column(Float, default=1000.0, nullable=False)
    initial_balance = Column(Float, default=1000.0, nullable=False)
    total_staked = Column(Float, default=0.0, nullable=False)
    total_pnl = Column(Float, default=0.0, nullable=False)
    
    total_bets = Column(Integer, default=0, nullable=False)
    greens = Column(Integer, default=0, nullable=False)
    reds = Column(Integer, default=0, nullable=False)
    voids = Column(Integer, default=0, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BankrollHistory(Base):
    __tablename__ = "bankroll_history"

    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, nullable=False)
    pnl_delta = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
