import math
import logging
from typing import Dict, Any, List, Optional, Tuple

# Fallback Configuration Logging Setup
try:
    from config import logger, DEFAULT_PAYOUT_RATE, KELLY_RISK_FRACTION
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("OTC_Enterprise_Quant.StatisticsEngine")
    DEFAULT_PAYOUT_RATE = 0.85
    KELLY_RISK_FRACTION = 0.5


class StatisticsEngine:
    """
    Master Quantitative Metrics & Statistical Risk Engine.
    Engineered for Quotex OTC Binary Options strictly focused on 1-Hour Executions.
    Computes Bayesian Win Probabilities, Trade Expectancy, Sharpe Ratio, Z-Score,
    Value at Risk (VaR), Profit Factor, Max Drawdown, and Dynamic Kelly Sizing.
    """

    def __init__(self, default_payout_rate: float = DEFAULT_PAYOUT_RATE):
        self.default_payout_rate = default_payout_rate

    def calculate_historical_win_rate(self, total_trades: int, total_wins: int) -> float:
        """Calculates simple historical win rate percentage."""
        if total_trades <= 0:
            return 50.0
        return round((total_wins / total_trades) * 100.0, 2)

    def calculate_bayesian_probability(
        self, 
        sample_wins: int, 
        sample_total: int, 
        prior_probability: float = 0.55, 
        prior_weight: int = 12
    ) -> float:
        """
        Uses Bayesian Updating with Laplace smoothing to prevent overfitting on small sample sizes.
        Smoothes empirical outcomes with prior model bias.
        """
        if sample_total == 0:
            return round(prior_probability * 100.0, 2)

        adjusted_wins = sample_wins + (prior_probability * prior_weight)
        adjusted_total = sample_total + prior_weight
        bayesian_win_rate = (adjusted_wins / adjusted_total) * 100.0

        return round(min(98.0, max(15.0, bayesian_win_rate)), 2)

    def calculate_trade_expectancy(
        self, 
        win_probability_pct: float, 
        payout_rate: Optional[float] = None
    ) -> float:
        """
        Calculates Expected Value (EV) per $1 trade unit.
        EV = (Win Prob * Payout) - (Loss Prob * 1.0)
        """
        payout = payout_rate if payout_rate is not None else self.default_payout_rate
        p_win = win_probability_pct / 100.0
        p_loss = 1.0 - p_win

        expectancy = (p_win * payout) - (p_loss * 1.0)
        return round(expectancy, 4)

    def calculate_z_score(self, win_rate_pct: float, total_samples: int, benchmark_pct: float = 50.0) -> float:
        """Computes Z-Score to verify if historical performance is statistically significant."""
        if total_samples <= 1:
            return 0.0

        p = win_rate_pct / 100.0
        p0 = benchmark_pct / 100.0
        standard_error = math.sqrt((p0 * (1.0 - p0)) / total_samples)

        if standard_error == 0:
            return 0.0

        return round((p - p0) / standard_error, 2)

    def calculate_sharpe_ratio(self, matched_history: List[Dict[str, Any]], payout_rate: float) -> float:
        """Computes empirical Sharpe Ratio based on historical trade outcomes."""
        if not matched_history or len(matched_history) < 2:
            return 0.0

        returns = []
        for item in matched_history:
            outcome = str(item.get("outcome", "")).upper()
            if outcome == "WIN":
                returns.append(payout_rate)
            elif outcome == "LOSS":
                returns.append(-1.0)

        if not returns:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        return round(mean_return / std_dev, 2)

    def calculate_streaks_and_profit_factor(
        self, 
        matched_history: List[Dict[str, Any]], 
        payout_rate: float
    ) -> Tuple[int, int, float]:
        """
        Calculates max consecutive wins, max consecutive losses, and profit factor.
        """
        if not matched_history:
            return 0, 0, 0.0

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        total_gross_profit = 0.0
        total_gross_loss = 0.0

        for item in matched_history:
            outcome = str(item.get("outcome", "")).upper()
            if outcome == "WIN":
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
                total_gross_profit += payout_rate
            elif outcome == "LOSS":
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
                total_gross_loss += 1.0

        profit_factor = round(total_gross_profit / total_gross_loss, 2) if total_gross_loss > 0 else (9.99 if total_gross_profit > 0 else 0.0)

        return max_wins, max_losses, profit_factor

    def compute_optimal_kelly_percentage(
        self, 
        win_rate_pct: float, 
        payout_rate: float = DEFAULT_PAYOUT_RATE
    ) -> float:
        """Calculates optimal fractional Kelly stake allocation percentage."""
        p = win_rate_pct / 100.0
        q = 1.0 - p
        b = payout_rate

        if b <= 0:
            return 0.0

        full_kelly = (b * p - q) / b
        fractional_kelly = max(0.0, full_kelly * KELLY_RISK_FRACTION)

        return round(fractional_kelly * 100, 2)

    def compute_quant_metrics(
        self, 
        matched_history: List[Dict[str, Any]], 
        model_confidence: float
    ) -> Dict[str, Any]:
        """
        Master Statistics Execution Pipeline.
        Evaluates historical database memory alongside vision AI confidence to produce deep quant metrics.
        """
        total_samples = len(matched_history)
        total_wins = sum(1 for item in matched_history if str(item.get("outcome", "")).upper() == "WIN")
        total_losses = sum(1 for item in matched_history if str(item.get("outcome", "")).upper() == "LOSS")
        
        empirical_win_rate = self.calculate_historical_win_rate(total_samples, total_wins)
        
        # Bayesian Win Rate Computation
        bayesian_prob = self.calculate_bayesian_probability(
            sample_wins=total_wins,
            sample_total=total_samples,
            prior_probability=(model_confidence / 100.0),
            prior_weight=12
        )

        expectancy = self.calculate_trade_expectancy(bayesian_prob, self.default_payout_rate)
        z_score = self.calculate_z_score(empirical_win_rate, total_samples)
        sharpe_ratio = self.calculate_sharpe_ratio(matched_history, self.default_payout_rate)
        max_wins, max_losses, profit_factor = self.calculate_streaks_and_profit_factor(matched_history, self.default_payout_rate)
        optimal_kelly_pct = self.compute_optimal_kelly_percentage(bayesian_prob, self.default_payout_rate)

        # Statistical significance check (95% confidence requires Z-Score >= 1.96 with N >= 25)
        is_statistically_significant = z_score >= 1.96 if total_samples >= 25 else False

        # Value at Risk (VaR 95% Estimation)
        var_95_pct = round(max(0.0, (1.0 - (bayesian_prob / 100.0)) * 100.0), 2)

        logger.info(
            f"Master Quant Metrics Computed | Samples: [{total_samples}] | "
            f"WinRate: [{empirical_win_rate}%] | BayesianProb: [{bayesian_prob}%] | "
            f"EV: [${expectancy}] | Sharpe: [{sharpe_ratio}] | ProfitFactor: [{profit_factor}]"
        )

        return {
            "sample_count": total_samples,
            "historical_wins": total_wins,
            "historical_losses": total_losses,
            "empirical_win_rate": empirical_win_rate,
            "bayesian_win_probability": bayesian_prob,
            "expected_value_per_dollar": expectancy,
            "z_score": z_score,
            "sharpe_ratio": sharpe_ratio,
            "profit_factor": profit_factor,
            "max_consecutive_wins": max_wins,
            "max_consecutive_losses": max_losses,
            "optimal_kelly_stake_pct": optimal_kelly_pct,
            "value_at_risk_95": var_95_pct,
            "statistically_significant": is_statistically_significant
        }


# Global Engine Instance Export
statistics_engine = StatisticsEngine()
# Class Alias for Flexible Import
QuantStatisticsEngine = StatisticsEngine

if __name__ == "__main__":
    print("Master Statistics Engine Ready.")
