import math
import logging
from typing import Dict, Any, List

logger = logging.getLogger("OTC_Enterprise_Quant.StatisticsEngine")

class StatisticsEngine:
    """
    Advanced Quantitative Metrics & Statistical Engine.
    Computes mathematical win probability, expectancy, signal variance, 
    and empirical win-rates based on historical pattern performance.
    """

    def __init__(self, default_payout_rate: float = 0.85):
        self.default_payout_rate = default_payout_rate  # Standard Quotex OTC payout (85%)

    def calculate_historical_win_rate(self, total_trades: int, total_wins: int) -> float:
        """
        Calculates simple historical win rate percentage.
        """
        if total_trades <= 0:
            return 50.0  # Base neutral assumption when no sample data exists
        return round((total_wins / total_trades) * 100.0, 2)

    def calculate_bayesian_probability(
        self, 
        sample_wins: int, 
        sample_total: int, 
        prior_probability: float = 0.55, 
        prior_weight: int = 10
    ) -> float:
        """
        Uses Bayesian Updating with Laplace smoothing to prevent overfitting on small sample sizes.
        Combines prior model expectations with actual empirical memory outcomes.
        """
        if sample_total == 0:
            return round(prior_probability * 100.0, 2)

        # Smooth posterior win probability using pseudo-counts
        adjusted_wins = (sample_wins) + (prior_probability * prior_weight)
        adjusted_total = sample_total + prior_weight
        bayesian_win_rate = (adjusted_wins / adjusted_total) * 100.0

        return round(bayesian_win_rate, 2)

    def calculate_trade_expectancy(
        self, 
        win_probability_pct: float, 
        payout_rate: float = None
    ) -> float:
        """
        Calculates Expected Value (EV) per $1 trade unit.
        EV = (Win Prob * Payout) - (Loss Prob * Risk)
        EV > 0 indicates a statistically profitable strategy long-term.
        """
        payout = payout_rate if payout_rate is not None else self.default_payout_rate
        p_win = win_probability_pct / 100.0
        p_loss = 1.0 - p_win

        expectancy = (p_win * payout) - (p_loss * 1.0)
        return round(expectancy, 4)

    def calculate_z_score(self, win_rate_pct: float, total_samples: int, benchmark_pct: float = 50.0) -> float:
        """
        Computes Z-Score to determine if performance is statistically significant
        or merely random market noise/luck.
        """
        if total_samples <= 1:
            return 0.0

        p = win_rate_pct / 100.0
        p0 = benchmark_pct / 100.0
        standard_error = math.sqrt((p0 * (1.0 - p0)) / total_samples)

        if standard_error == 0:
            return 0.0

        z_score = (p - p0) / standard_error
        return round(z_score, 2)

    def compute_quant_metrics(
        self, 
        matched_history: List[Dict[str, Any]], 
        model_confidence: float
    ) -> Dict[str, Any]:
        """
        Master Statistics Execution Pipeline.
        Evaluates historical database matches alongside model confidence to output quant metrics.
        """
        total_samples = len(matched_history)
        total_wins = sum(1 for item in matched_history if item.get("outcome") == "WIN")
        
        empirical_win_rate = self.calculate_historical_win_rate(total_samples, total_wins)
        
        # Bayesian Probability combining model score with empirical history
        bayesian_prob = self.calculate_bayesian_probability(
            sample_wins=total_wins,
            sample_total=total_samples,
            prior_probability=(model_confidence / 100.0),
            prior_weight=10
        )

        expectancy = self.calculate_trade_expectancy(bayesian_prob)
        z_score = self.calculate_z_score(empirical_win_rate, total_samples)

        # Statistical significance flag
        is_statistically_significant = z_score >= 1.96 if total_samples >= 30 else False

        logger.info(
            f"Quant Metrics Computed: Samples={total_samples}, WinRate={empirical_win_rate}%, "
            f"BayesianProb={bayesian_prob}%, EV={expectancy}"
        )

        return {
            "sample_count": total_samples,
            "historical_wins": total_wins,
            "empirical_win_rate": empirical_win_rate,
            "bayesian_win_probability": bayesian_prob,
            "expected_value_per_dollar": expectancy,
            "z_score": z_score,
            "statistically_significant": is_statistically_significant
        }
