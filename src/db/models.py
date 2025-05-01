from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Token(Base):
    """Model for tracking monitored tokens"""
    __tablename__ = 'tokens'

    id = Column(Integer, primary_key=True)
    coin_type = Column(String, unique=True, nullable=False)
    symbol = Column(String, nullable=False)
    name = Column(String)
    market_cap = Column(Float)
    price_usd = Column(Float)
    volume_24h = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    whale_holders = relationship("WhaleHolder", back_populates="token")
    whale_movements = relationship("WhaleMovement", back_populates="token")

class WhaleHolder(Base):
    """Model for tracking large token holders"""
    __tablename__ = 'whale_holders'

    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey('tokens.id'), nullable=False)
    address = Column(String, nullable=False)
    balance = Column(Float, nullable=False)
    usd_value = Column(Float, nullable=False)
    percentage = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    token = relationship("Token", back_populates="whale_holders")
    movements = relationship("WhaleMovement", back_populates="holder")

    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('token_id', 'address', sqlite_on_conflict='REPLACE'),
    )

class WhaleMovement(Base):
    """Model for tracking whale token movements"""
    __tablename__ = 'whale_movements'

    id = Column(Integer, primary_key=True)
    token_id = Column(Integer, ForeignKey('tokens.id'), nullable=False)
    holder_id = Column(Integer, ForeignKey('whale_holders.id'), nullable=False)
    movement_type = Column(String, nullable=False)  # 'buy' or 'sell'
    amount = Column(Float, nullable=False)
    usd_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    token = relationship("Token", back_populates="whale_movements")
    holder = relationship("WhaleHolder", back_populates="movements")

class WalletStats(Base):
    """Model for tracking wallet statistics"""
    __tablename__ = 'wallet_stats'

    id = Column(Integer, primary_key=True)
    address = Column(String, unique=True, nullable=False)
    total_volume_usd = Column(Float, default=0)
    total_trades = Column(Integer, default=0)
    total_pnl_usd = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def win_rate(self) -> float:
        """Calculate win rate based on PnL"""
        if self.total_trades == 0:
            return 0.0
        return (self.total_pnl_usd / self.total_volume_usd) * 100 if self.total_volume_usd > 0 else 0.0