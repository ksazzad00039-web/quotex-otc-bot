import os
import io
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Fallback Configuration Logging Setup
try:
    from config import logger
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("OTC_Enterprise_Quant.OutcomeEngine")


class OutcomeEngine:
    """
    Enterprise-Grade Trade Outcome Verification & Reinforcement Memory Engine.
    Evaluates real-time execution results (WIN, LOSS, REFUND) for 1-Hour & 1-Day chart signals,
    computes Bayesian Expectancy Metrics, and persists analytics to JSON & Database engines.
    """

    def __init__(self, log_filepath: str = "trade_memory.json"):
        self.log_filepath = log_filepath
        self._ensure_storage_ready()

    def _ensure_storage_ready(self) -> None:
        """Ensures that the memory storage JSON structure is properly initialized."""
        if not os.path.exists(self.log_filepath):
            try:
                with open(self.log_filepath, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=4)
                logger.info(f"Initialized Trade Outcome Memory File: [{self.log_filepath}]")
            except Exception as e:
                logger.error(f"Failed to create trade memory storage: {str(e)}")

    def evaluate_result(self, entry_price: float, exit_price: float, predicted_direction: str) -> str:
        """
        Determines trade execution outcome based on precise entry vs. exit price metrics.
        """
        if abs(entry_price - exit_price) < 1e-7:
            return "REFUND"

        if predicted_direction.upper() == "UP":
            return "WIN" if exit_price > entry_price else "LOSS"
        elif predicted_direction.upper() == "DOWN":
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
        quant_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Master Execution Pipeline:
        Processes trade completion, updates PnL, calculates price delta, 
        and stores structural analytics for ML model reinforcement.
        """
        if quant_metrics is None:
            quant_metrics = {}

        outcome = self.evaluate_result(entry_price, exit_price, predicted_direction)
        price_delta = round(abs(exit_price - entry_price), 5)

        record = {
            "signal_id": signal_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "asset_pair": asset_pair,
            "timeframe": timeframe.upper(),
            "predicted_direction": predicted_direction.upper(),
            "confidence_score": float(confidence_score),
            "entry_price": float(entry_price),
            "exit_price": float(exit_price),
            "price_delta": price_delta,
            "outcome": outcome,
            "bayesian_probability": float(quant_metrics.get("bayesian_win_probability", confidence_score)),
            "expected_value": float(quant_metrics.get("expected_value_per_dollar", 0.0)),
            "smc_confluence_score": float(quant_metrics.get("liquidity_score", 50.0)),
            "reinforcement_ready": True
        }

        # Persist locally to JSON storage
        self._persist_to_local_storage(record)

        # Sync with Primary Turso Database if accessible
        self._sync_with_database(record)

        logger.info(
            f"Trade Outcome Recorded | Signal: [{signal_id}] | Asset: [{asset_pair}] | "
            f"Prediction: [{predicted_direction}] | Outcome: [{outcome}]"
        )
        return record

    def _persist_to_local_storage(self, record: Dict[str, Any]) -> None:
        """Appends the trade record to local JSON persistent memory safely."""
        try:
            records = []
            if os.path.exists(self.log_filepath):
                try:
                    with open(self.log_filepath, "r", encoding="utf-8") as f:
                        records = json.load(f)
                except json.JSONDecodeError:
                    records = []

            records.append(record)

            with open(self.log_filepath, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=4, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to persist trade outcome to JSON: {str(e)}")

    def _sync_with_database(self, record: Dict[str, Any]) -> None:
        """Syncs recorded outcome metrics with database layer if database module exists."""
        try:
            from database import db
            if hasattr(db, "record_trade_result"):
                db.record_trade_result(record)
                logger.info(f"Outcome synced to Turso/SQLite DB for Signal ID: [{record['signal_id']}]")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Database sync bypass: {str(e)}")

    def calculate_historical_performance(self) -> Dict[str, Any]:
        """Calculates global win rate, total trades, and historical stats from stored memory."""
        try:
            if not os.path.exists(self.log_filepath):
                return self._build_empty_stats()

            with open(self.log_filepath, "r", encoding="utf-8") as f:
                records = json.load(f)

            if not records:
                return self._build_empty_stats()

            total_trades = len(records)
            wins = sum(1 for r in records if r.get("outcome") == "WIN")
            losses = sum(1 for r in records if r.get("outcome") == "LOSS")
            refunds = sum(1 for r in records if r.get("outcome") == "REFUND")

            effective_trades = wins + losses
            win_rate = round((wins / effective_trades) * 100, 2) if effective_trades > 0 else 0.0

            return {
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "refunds": refunds,
                "win_rate_percentage": win_rate,
                "effective_sample_size": effective_trades
            }

        except Exception as e:
            logger.error(f"Failed to calculate historical metrics: {str(e)}")
            return self._build_empty_stats()

    def _build_empty_stats(self) -> Dict[str, Any]:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "refunds": 0,
            "win_rate_percentage": 0.0,
            "effective_sample_size": 0
        }


# Global Instance Export
outcome_engine = OutcomeEngine()
# Class Alias for Flexible Importing
TradeOutcomeEngine = OutcomeEngine

if __name__ == "__main__":
    print("Trade Outcome Engine Module Ready.")
