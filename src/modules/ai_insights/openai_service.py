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
            # Format whale stats for the prompt
            stats_text = self._format_whale_stats(whale_stats)
            
            # Generate insights
            insight = self.chain.run({
                "token_symbol": token_symbol,
                "movement_type": movement_data["movement_type"],
                "amount": movement_data["amount"],
                "usd_value": movement_data["usd_value"],
                "whale_stats": stats_text
            })
            
            return insight.strip()
            
        except Exception as e:
            print(f"Error generating insights: {e}")
            return "Unable to generate insights at this time."
    
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