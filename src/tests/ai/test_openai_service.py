from unittest.mock import patch, Mock
import pytest
from modules.ai_insights.openai_service import WhaleInsightGenerator

@pytest.fixture
def mock_movement_data():
    return {
        "movement_type": "buy",
        "amount": 10000,
        "usd_value": 15500
    }

@pytest.fixture
def mock_whale_stats():
    return {
        "win_rate": 67.5,
        "total_trades": 100,
        "total_volume_usd": 500000,
        "total_pnl_usd": 25000,
        "current_holdings": [
            {
                "token": "LOFI",
                "usd_value": 50000,
                "percentage": 2.5
            }
        ],
        "recent_movements": [
            {
                "token": "LOFI",
                "type": "buy",
                "usd_value": 15500,
                "timestamp": "2024-03-15T12:00:00"
            }
        ]
    }

def test_generate_short_insight():
    generator = WhaleInsightGenerator()
    
    # Test smart whale with high win rate
    insight = generator.generate_short_insight(
        win_rate=67.5,
        movement_type="buy",
        amount_usd=15500,
        token_symbol="LOFI"
    )
    assert "🐋" in insight  # Smart whale emoji
    assert "smart whale" in insight.lower()
    assert "$15.5K" in insight
    assert "67.5%" in insight
    assert "strong bullish signal" in insight.lower()
    
    # Test risky whale with low win rate
    insight = generator.generate_short_insight(
        win_rate=32.1,
        movement_type="sell",
        amount_usd=8750,
        token_symbol="LOFI"
    )
    assert "⚠️" in insight  # Warning emoji
    assert "risky whale" in insight.lower()
    assert "$8.8K" in insight
    assert "32.1%" in insight
    assert "high-risk movement" in insight.lower()
    
    # Test edge case with small amount
    insight = generator.generate_short_insight(
        win_rate=51.2,
        movement_type="buy",
        amount_usd=950,
        token_symbol="LOFI"
    )
    assert "🐋" in insight
    assert "smart whale" in insight.lower()
    assert "$950" in insight
    assert "51.2%" in insight
    assert "could signal a trend shift" in insight.lower()

@patch('langchain.chains.LLMChain.invoke')
def test_generate_movement_insight(mock_invoke, mock_movement_data, mock_whale_stats):
    generator = WhaleInsightGenerator()
    
    # Mock the LLMChain response
    detailed_insight = """
🔍 Movement Analysis:
- Large buy of 10,000 LOFI tokens
- Above average trade size
- Significant volume impact

📊 Market Impact Analysis:
- Immediate price impact prediction
- Volume impact analysis
- Potential chain reaction

📈 Trading Opportunities:
- Entry/Exit points to consider
- Risk management suggestions
- Specific price levels to watch
- Time frames for the opportunity

💡 Strategic Recommendations:
- Short-term trading strategy (24h)
- Medium-term outlook (1-2 weeks)
- Risk/reward scenarios
- Stop-loss and take-profit suggestions

⚠️ Risk Factors:
- Key risks to consider
- Market conditions to watch
- Warning signs to monitor
"""
    mock_response = Mock()
    mock_response.content = detailed_insight
    mock_invoke.return_value = mock_response
    
    # Generate insight
    insight = generator.generate_movement_insight(
        token_symbol="LOFI",
        movement_data=mock_movement_data,
        whale_stats=mock_whale_stats
    )
    
    # Verify the short insight is present
    assert "🐋" in insight
    assert "smart whale" in insight.lower()
    assert mock_movement_data["movement_type"] in insight.lower()
    assert str(mock_whale_stats["win_rate"]) in insight
    
    # Verify the detailed insight is present
    assert "🔍 Movement Analysis:" in insight
    assert "📊 Market Impact Analysis:" in insight
    assert "📈 Trading Opportunities:" in insight
    assert "💡 Strategic Recommendations:" in insight
    assert "⚠️ Risk Factors:" in insight
    
    # Verify proper formatting
    assert "\n\n" in insight  # Check for separation between short and detailed insights
    
    # Verify the context was properly passed to LLMChain
    mock_invoke.assert_called_once()
    call_args = mock_invoke.call_args[0][0]
    assert "token_symbol" in call_args
    assert "movement_type" in call_args
    assert "amount" in call_args
    assert "usd_value" in call_args
    assert "whale_stats" in call_args

def test_format_whale_stats(mock_whale_stats):
    generator = WhaleInsightGenerator()
    stats_text = generator._format_whale_stats(mock_whale_stats)
    
    assert "Win Rate: 67.50%" in stats_text
    assert "Total Trades: 100" in stats_text
    assert "Total Volume: $500,000.00" in stats_text
    assert "PnL Status: Positive" in stats_text
    assert "Average Trade Size: $5,000.00" in stats_text
    assert "LOFI: $50,000.00 (2.50%)" in stats_text
    assert "LOFI buy: $15,500.00" in stats_text

def test_format_whale_stats_empty():
    generator = WhaleInsightGenerator()
    stats_text = generator._format_whale_stats({})
    assert "No historical data available for this whale" in stats_text

def test_format_holdings_empty():
    generator = WhaleInsightGenerator()
    holdings_text = generator._format_holdings([])
    assert "No current holdings data" in holdings_text

def test_format_recent_movements_empty():
    generator = WhaleInsightGenerator()
    movements_text = generator._format_recent_movements([])
    assert "No recent movement data" in movements_text

def test_generate_concise_whale_insight():
    generator = WhaleInsightGenerator()
    
    # Test case 1: Smart whale with large trade
    stats = {
        "win_rate": 67.5,
        "total_trades": 4851,
        "total_volume_usd": 4682921.12,
        "average_trade": 965.35,
        "total_pnl_usd": 50000
    }
    
    movement = {
        "token_symbol": "LOFI",
        "movement_type": "buy",
        "usd_value": 1500.00,
        "amount": 32111.02
    }
    
    insight = generator.generate_concise_whale_insight(stats, movement)
    
    # Verify format and content
    assert "🐋" in insight  # Smart whale emoji
    assert "$4.7M" in insight  # Total volume
    assert "$1.5K" in insight  # Trade value
    assert "67.5%" in insight  # Win rate
    assert "above" in insight.lower()  # Trade size context
    assert "📈" in insight  # Positive PnL emoji
    assert "Profitable trader" in insight
    assert "🔥" in insight  # High confidence emoji
    
    # Test case 2: Risky whale with small trade
    stats = {
        "win_rate": 31.5,
        "total_trades": 100,
        "total_volume_usd": 50000,
        "average_trade": 500,
        "total_pnl_usd": -5000
    }
    
    movement = {
        "token_symbol": "LOFI",
        "movement_type": "sell",
        "usd_value": 300.00,
        "amount": 1000
    }
    
    insight = generator.generate_concise_whale_insight(stats, movement)
    
    # Verify format and content
    assert "⚠️" in insight  # Risky whale emoji
    assert "$50.0K" in insight  # Total volume
    assert "$300" in insight  # Trade value
    assert "31.5%" in insight  # Win rate
    assert "below" in insight.lower()  # Trade size context
    assert "📉" in insight  # Negative PnL emoji
    assert "Losing trader" in insight
    assert "💸" in insight  # Speculative move emoji
    
    # Test case 3: With hashtags
    insight = generator.generate_concise_whale_insight(stats, movement, include_hashtags=True)
    assert "#LOFI" in insight
    assert "#CryptoWhale" in insight
    assert "#WhaleAlert" in insight

def test_generate_concise_whale_insight_error_handling():
    generator = WhaleInsightGenerator()
    
    # Test with missing data
    stats = {}
    movement = {}
    
    insight = generator.generate_concise_whale_insight(stats, movement)
    assert "Unable to generate concise insight" in insight 