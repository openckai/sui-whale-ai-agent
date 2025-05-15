from unittest.mock import patch, Mock

@patch('langchain.chains.LLMChain.invoke')
def test_generate_insight(mock_invoke, mock_db, mock_movement, mock_token, mock_whale_context):
    generator = InsightGenerator(mock_db)
    
    # Mock the get_whale_context method
    generator.get_whale_context = Mock(return_value=mock_whale_context)
    
    # Mock the LLMChain response
    detailed_insight = """
## 📊 Movement Analysis
- Large buy of 10,000 LOFI tokens
- Above average trade size
- Significant volume impact

## 🐋 Whale Profile
- Successful trader with 65.5% win rate
- High frequency trading style
- Improving performance trend

## 💡 Strategic Insights
- Consider following this whale's moves
- Watch for continuation of accumulation
- Set entries near whale's average price

## ⚠️ Risk Assessment
- Market volatility warning
- Monitor for trend reversal
- Set stop losses appropriately

## 💪 Opportunity Score
8/10 - Strong whale with proven track record
"""
    mock_response = Mock()
    mock_response.content = detailed_insight
    mock_invoke.return_value = mock_response
    
    # Generate insight
    insight = generator.generate_insight(mock_movement, mock_token)
    
    # Verify the short insight is present
    assert "🐋" in insight
    assert "smart whale" in insight.lower()
    assert mock_movement.movement_type in insight.lower()
    assert str(mock_whale_context.win_rate) in insight
    
    # Verify the detailed insight is present
    assert "## 📊 Movement Analysis" in insight
    assert "## 🐋 Whale Profile" in insight
    assert "## 💡 Strategic Insights" in insight
    assert "## ⚠️ Risk Assessment" in insight
    assert "## 💪 Opportunity Score" in insight
    
    # Verify proper formatting
    assert "\n\n" in insight  # Check for separation between short and detailed insights
    
    # Verify the context was properly passed to LLMChain
    mock_invoke.assert_called_once()
    call_args = mock_invoke.call_args[0][0]
    assert "movement_details" in call_args
    assert "whale_context" in call_args
    assert "market_context" in call_args

def test_generate_short_insight(mock_db):
    generator = InsightGenerator(mock_db)
    
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