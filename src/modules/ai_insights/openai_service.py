from typing import Dict, List
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

class WhaleInsightGenerator:
    def __init__(self):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-3.5-turbo",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Template for analyzing whale movements
        self.movement_template = PromptTemplate(
            input_variables=["token_symbol", "movement_type", "amount", "usd_value", "whale_stats"],
            template="""
            You are an expert crypto analyst specializing in whale movement analysis. Analyze this whale movement and provide detailed strategic insights:
            
            Token: {token_symbol}
            Action: {movement_type}
            Amount: {amount} tokens
            USD Value: ${usd_value}
            
            Whale Stats:
            {whale_stats}
            
            Please provide a comprehensive analysis with the following structure:

            🔍 Movement Analysis:
            - Significance of this movement relative to whale's history
            - Compare this trade size to their average ($)
            - Context of their win rate and overall performance
            
            📊 Market Impact Analysis:
            - Immediate price impact prediction
            - Volume impact analysis
            - Potential chain reaction from other traders
            
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
            
            Keep insights actionable and specific. Include numerical values where possible (prices, percentages, time frames).
            Focus on helping traders identify and execute opportunities while managing risks.
            """
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.movement_template)
    
    def generate_movement_insight(
        self,
        token_symbol: str,
        movement_data: Dict,
        whale_stats: Dict
    ) -> str:
        """Generate AI insights for a whale movement"""
        try:
            # Generate short insight first
            short_insight = self.generate_short_insight(
                win_rate=whale_stats.get('win_rate', 0),
                movement_type=movement_data['movement_type'],
                amount_usd=movement_data['usd_value'],
                token_symbol=token_symbol
            )
            
            # Format whale stats for the prompt
            stats_text = self._format_whale_stats(whale_stats)
            
            # Generate detailed insights
            response = self.chain.invoke({
                "token_symbol": token_symbol,
                "movement_type": movement_data["movement_type"],
                "amount": movement_data["amount"],
                "usd_value": movement_data["usd_value"],
                "whale_stats": stats_text
            })
            
            # Extract the text from the response
            detailed_insight = ""
            if hasattr(response, 'content'):
                detailed_insight = response.content.strip()
            else:
                detailed_insight = str(response).strip()
            
            # Combine insights
            return f"{short_insight}\n\n{detailed_insight}"
            
        except Exception as e:
            print(f"Error generating insights: {e}")
            return "Unable to generate insights at this time."
    
    def generate_short_insight(self, win_rate: float, movement_type: str, amount_usd: float, token_symbol: str) -> str:
        """Generate a short, high-signal insight for whale alerts.
        
        Args:
            win_rate (float): The whale's win rate percentage
            movement_type (str): Type of movement (buy/sell)
            amount_usd (float): USD value of the movement
            token_symbol (str): Token symbol (e.g. 'LOFI')
            
        Returns:
            str: A markdown-formatted insight string
        """
        # Format USD amount (e.g. 15500 -> $15.5K)
        formatted_amount = f"${amount_usd/1000:.1f}K" if amount_usd >= 1000 else f"${amount_usd:.0f}"
        
        # Determine whale intelligence indicator
        whale_type = "smart" if win_rate > 50 else "risky"
        whale_emoji = "🐋" if win_rate > 50 else "⚠️"
        
        # Generate action description
        action = f"{whale_emoji} A {whale_type} whale just {movement_type}ed **{formatted_amount} of ${token_symbol}**"
        
        # Generate win rate context
        signal = ""
        if win_rate > 65:
            signal = "strong bullish signal"
        elif win_rate > 50:
            signal = "could signal a trend shift"
        elif win_rate < 35:
            signal = "high-risk movement"
        else:
            signal = "proceed with caution"
            
        # Format win rate with emoji
        win_rate_line = f"📈 Win Rate: {win_rate:.1f}% — {signal}"
        
        # Combine into final insight
        return f"{action}\n{win_rate_line}"
    
    def _format_whale_stats(self, stats: Dict) -> str:
        """Format whale statistics for the prompt"""
        if not stats:
            return "No historical data available for this whale."
            
        return f"""
        Win Rate: {stats.get('win_rate', 0):.2f}%
        Total Trades: {stats.get('total_trades', 0)}
        Total Volume: ${stats.get('total_volume_usd', 0):,.2f}
        PnL Status: {'Positive' if stats.get('total_pnl_usd', 0) > 0 else 'Negative'}
        Average Trade Size: ${stats.get('total_volume_usd', 0) / stats.get('total_trades', 1):,.2f}
        Recent Holdings: {self._format_holdings(stats.get('current_holdings', []))}
        Recent Movements: {self._format_recent_movements(stats.get('recent_movements', []))}
        """
    
    def _format_holdings(self, holdings: List[Dict]) -> str:
        """Format current holdings for the prompt"""
        if not holdings:
            return "No current holdings data"
            
        holdings_text = []
        for h in holdings:
            holdings_text.append(
                f"${h['token']}: ${h['usd_value']:,.2f} ({h['percentage']:.2f}%)"
            )
        return ", ".join(holdings_text)

    def _format_recent_movements(self, movements: List[Dict]) -> str:
        """Format recent movements for context"""
        if not movements:
            return "No recent movement data"
            
        movement_text = []
        for m in movements:
            movement_text.append(
                f"{m['token']} {m['type']}: ${m['usd_value']:,.2f}"
            )
        return " | ".join(movement_text)

    def generate_concise_whale_insight(self, stats: Dict, movement: Dict, include_hashtags: bool = False) -> str:
        """Generate a short, trader-friendly insight for whale movements.
        
        Args:
            stats (Dict): Whale statistics including win rate, trades, volume, etc.
            movement (Dict): Current movement details including token, type, value
            include_hashtags (bool): Whether to append relevant hashtags
            
        Returns:
            str: A concise, emoji-rich insight string
        """
        try:
            # Format key numbers
            volume_str = f"${stats['total_volume_usd']/1_000_000:.1f}M" if stats['total_volume_usd'] >= 1_000_000 else f"${stats['total_volume_usd']/1_000:.1f}K"
            trade_value_str = f"${movement['usd_value']/1_000:.1f}K" if movement['usd_value'] >= 1_000 else f"${movement['usd_value']:.0f}"
            avg_trade_str = f"${stats['average_trade']/1_000:.1f}K" if stats['average_trade'] >= 1_000 else f"${stats['average_trade']:.0f}"
            pnl_str = f"${abs(stats['total_pnl_usd'])/1_000:.1f}K"
            
            # Determine trade size context
            size_context = "above" if movement['usd_value'] > stats['average_trade'] else "below"
            
            # Determine trader quality indicators
            is_smart = stats['win_rate'] > 50
            whale_emoji = "🐋" if is_smart else "⚠️"
            pnl_emoji = "📈" if stats['total_pnl_usd'] > 0 else "📉"
            
            # Generate main insight
            main_line = (
                f"{whale_emoji} A ${movement['token_symbol']} whale with a {stats['win_rate']:.1f}% win rate "
                f"and {volume_str} total volume just {movement['movement_type']}ed {trade_value_str} — "
                f"{size_context} their {avg_trade_str} average."
            )
            
            # Generate PnL context
            pnl_context = (
                f"{'Profitable' if stats['total_pnl_usd'] > 0 else 'Losing'} trader "
                f"({pnl_emoji} {pnl_str} PnL)"
            )
            
            # Generate strategic insight
            strategy_line = ""
            if is_smart and movement['usd_value'] > stats['average_trade']:
                strategy_line = "🔥 High-confidence move — potential trend signal."
            elif is_smart:
                strategy_line = "✅ Worth monitoring for position buildup."
            elif movement['usd_value'] > stats['average_trade'] * 1.5:
                strategy_line = "🕵️ Large move from risky trader — watch for reversal."
            else:
                strategy_line = "💸 Speculative move — wait for confirmation."
            
            # Combine insights
            insight = f"{main_line}\n{pnl_context} — {strategy_line}"
            
            # Add hashtags if requested
            if include_hashtags:
                hashtags = f"\n\n#{movement['token_symbol']} #CryptoWhale #WhaleAlert"
                insight += hashtags
            
            return insight
            
        except Exception as e:
            print(f"Error generating concise insight: {e}")
            return "Unable to generate concise insight." 