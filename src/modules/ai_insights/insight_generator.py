    def generate_insight(self, movement: WhaleMovement, token: Token) -> str:
        """Generate comprehensive AI insight for a whale movement"""
        try:
            # Get whale context
            whale_context = self.get_whale_context(movement.holder.address, token)
            if not whale_context:
                return "Insufficient data for analysis"

            # Generate short insight first
            short_insight = self.generate_short_insight(
                win_rate=whale_context.win_rate,
                movement_type=movement.movement_type,
                amount_usd=movement.usd_value,
                token_symbol=token.symbol
            )

            # Format all contexts for detailed insight
            movement_details = self.format_movement_details(movement, token)
            whale_context_str = self.format_whale_context(whale_context)
            market_context = self.format_market_context(token)

            # Generate detailed insight using invoke
            response = self.chain.invoke({
                "movement_details": movement_details,
                "whale_context": whale_context_str,
                "market_context": market_context,
                "system_prompt": self.system_prompt
            })

            # Extract the text from the response and combine with short insight
            detailed_insight = ""
            if hasattr(response, 'content'):
                detailed_insight = response.content.strip()
            else:
                detailed_insight = str(response).strip()

            # Return combined insights
            return f"{short_insight}\n\n{detailed_insight}"

        except Exception as e:
            print(f"Error generating insight: {e}")
            return "Error generating insight"

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