import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("OTC_Enterprise_Quant.OutcomeEngine")

class OutcomeEngine:
    """
    Trade Outcome Engine & Memory Logger.
    Tracks execution outcomes (WIN / LOSS / REFUND), validates actual price movement
    against system predictions, and logs execution analytics for model reinforcement.
    """

    def __init__(self, log_filepath: str = "trade_memory.json"):
        self.log_filepath = log_filepath

    def evaluate_result(self, entry_price: float, exit_price: float, predicted_direction: str) -> str:
        """
        Determines the precise trade outcome based on entry vs exit price.
        """
        if entry_price == exit_price:
            return "REFUND"

        if predicted_direction == "UP":
            return "WIN" if exit_price > entry_price else "LOSS"
        elif predicted_direction == "DOWN":
            return "WIN" if exit_price < entry_price else "LOSS"

        return "INVALID"

    def record_outcome(
        self,
        signal_id: str,
        asset_pair: str,
        timeframe: str,
        predicted_direction: str,
        confidence_score: float,
        entry_price: float,
        exit_price: float,
        quant_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Processes trade completion data, computes PnL metrics, and updates memory record.
        """
        outcome = self.evaluate_result(entry_price, exit_price, predicted_direction)
        price_delta = round(abs(exit_price - entry_price), 5)

        record = {
            "signal_id": signal_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "asset_pair": asset_pair,
            "timeframe": timeframe,
            "predicted_direction": predicted_direction,
            "confidence_score": confidence_score,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "price_delta": price_delta,
            "outcome": outcome,
            "bayesian_probability": quant_metrics.get("bayesian_win_probability", 0.0),
            "expected_value": quant_metrics.get("expected_value_per_dollar", 0.0)
        }

        self._persist_to_storage(record)
        logger.info(f"Outcome Logged | Signal ID: {signal_id} | Result: {outcome} | Asset: {asset_pair}")
        return record

    def _persist_to_storage(self, record: Dict[str, Any]) -> None:
        """
        Appends the trade record to a local JSON persistent storage file.
        """
        try:
            records = []
            try:
                with open(self.log_filepath, "r", encoding="utf-8") as f:
                    records = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                records = []

            records.append(record)

            with open(self.log_filepath, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=4, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to persist trade outcome: {str(e)}")

