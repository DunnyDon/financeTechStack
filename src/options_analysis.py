"""
Options Strategy Analysis Module

Greeks calculations and options position tracking:
- Delta, Gamma, Theta, Vega, Rho calculations
- Implied volatility estimation
- Option position tracking
- Strategy analysis (spreads, straddles, etc.)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GreeksResult:
    """Result of Greeks calculations."""

    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class OptionsAnalysis:
    """Analyze options positions and calculate Greeks."""

    @staticmethod
    def calculate_greeks(
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float = 0.04,
        option_type: str = "call",
    ) -> GreeksResult:
        """
        Calculate Black-Scholes Greeks.

        Args:
            spot_price: Current stock price
            strike_price: Option strike price
            time_to_expiry: Years to expiration
            volatility: Annualized volatility
            risk_free_rate: Risk-free rate
            option_type: "call" or "put"

        Returns:
            GreeksResult with all Greeks
        """
        if time_to_expiry <= 0:
            # Expiration: Greeks approach limit values
            if option_type == "call":
                delta = 1.0 if spot_price > strike_price else 0.0
            else:
                delta = -1.0 if spot_price < strike_price else 0.0

            return GreeksResult(delta=delta, gamma=0.0, theta=0.0, vega=0.0, rho=0.0)

        # Prevent division by zero and invalid volatility
        if volatility <= 0:
            volatility = 0.01

        d1 = (
            np.log(spot_price / strike_price)
            + (risk_free_rate + 0.5 * volatility**2) * time_to_expiry
        ) / (volatility * np.sqrt(time_to_expiry))
        d2 = d1 - volatility * np.sqrt(time_to_expiry)

        # Standard normal PDF and CDF
        pdf_d1 = np.exp(-(d1**2) / 2) / np.sqrt(2 * np.pi)
        cdf_d1 = 0.5 * (1 + np.tanh(0.797 * d1))  # Approximation of norm.cdf
        cdf_d2 = 0.5 * (1 + np.tanh(0.797 * d2))

        if option_type == "call":
            delta = cdf_d1
            theta = (
                -spot_price * pdf_d1 * volatility / (2 * np.sqrt(time_to_expiry))
                - risk_free_rate * strike_price * np.exp(-risk_free_rate * time_to_expiry) * cdf_d2
            )
            rho = strike_price * time_to_expiry * np.exp(-risk_free_rate * time_to_expiry) * cdf_d2
        else:  # put
            delta = cdf_d1 - 1
            theta = (
                -spot_price * pdf_d1 * volatility / (2 * np.sqrt(time_to_expiry))
                + risk_free_rate * strike_price * np.exp(-risk_free_rate * time_to_expiry) * (1 - cdf_d2)
            )
            rho = (
                -strike_price * time_to_expiry * np.exp(-risk_free_rate * time_to_expiry) * (1 - cdf_d2)
            )

        gamma = pdf_d1 / (spot_price * volatility * np.sqrt(time_to_expiry))
        vega = spot_price * pdf_d1 * np.sqrt(time_to_expiry) / 100  # Per 1% change
        theta = theta / 365  # Convert to per day

        return GreeksResult(
            delta=float(delta),
            gamma=float(gamma),
            theta=float(theta),
            vega=float(vega),
            rho=float(rho),
        )

    @staticmethod
    def estimate_implied_volatility(
        option_price: float,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float = 0.04,
        option_type: str = "call",
        initial_guess: float = 0.20,
    ) -> float:
        """
        Estimate implied volatility using Newton-Raphson method.

        Args:
            option_price: Current market price of option
            spot_price: Current stock price
            strike_price: Strike price
            time_to_expiry: Years to expiration
            risk_free_rate: Risk-free rate
            option_type: "call" or "put"
            initial_guess: Starting volatility guess

        Returns:
            Estimated implied volatility
        """
        volatility = initial_guess
        max_iterations = 100
        tolerance = 1e-6

        for _ in range(max_iterations):
            greeks = OptionsAnalysis.calculate_greeks(
                spot_price, strike_price, time_to_expiry, volatility, risk_free_rate, option_type
            )

            # Simple BS price calculation
            d1 = (
                np.log(spot_price / strike_price)
                + (risk_free_rate + 0.5 * volatility**2) * time_to_expiry
            ) / (volatility * np.sqrt(time_to_expiry))
            d2 = d1 - volatility * np.sqrt(time_to_expiry)

            cdf_d1 = 0.5 * (1 + np.tanh(0.797 * d1))
            cdf_d2 = 0.5 * (1 + np.tanh(0.797 * d2))

            if option_type == "call":
                bs_price = spot_price * cdf_d1 - strike_price * np.exp(-risk_free_rate * time_to_expiry) * cdf_d2
            else:
                bs_price = (
                    strike_price * np.exp(-risk_free_rate * time_to_expiry) * (1 - cdf_d2)
                    - spot_price * (1 - cdf_d1)
                )

            price_diff = bs_price - option_price

            # Vega as denominator for Newton-Raphson
            if abs(greeks.vega) < 1e-6:
                break

            volatility -= price_diff / (greeks.vega * 100)  # Adjust for vega scale

            if abs(price_diff) < tolerance:
                break

            # Ensure positive volatility
            volatility = max(0.001, volatility)

        return float(max(0.001, volatility))

    @staticmethod
    def analyze_position(
        positions: List[Dict], spot_price: float, risk_free_rate: float = 0.04
    ) -> Dict[str, any]:
        """
        Analyze multiple option positions (strategy).

        Args:
            positions: List of dicts with 'type', 'strike', 'expiry_days', 'price', 'quantity'
            spot_price: Current spot price
            risk_free_rate: Risk-free rate

        Returns:
            Strategy analysis with Greeks and P&L
        """
        time_to_expiry = 30 / 365  # Default: assume 30 days if not specified

        greeks_agg = {
            "delta": 0.0,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
            "rho": 0.0,
        }

        positions_detail = []

        for pos in positions:
            opt_type = pos.get("type", "call")  # call or put
            strike = pos.get("strike", spot_price)
            expiry_days = pos.get("expiry_days", 30)
            qty = pos.get("quantity", 1)

            time_to_expiry = expiry_days / 365

            greeks = OptionsAnalysis.calculate_greeks(
                spot_price, strike, time_to_expiry, 0.20, risk_free_rate, opt_type
            )

            position_detail = {
                "type": opt_type,
                "strike": strike,
                "quantity": qty,
                "delta": greeks.delta * qty,
                "gamma": greeks.gamma * qty,
                "theta": greeks.theta * qty,
                "vega": greeks.vega * qty,
                "rho": greeks.rho * qty,
            }

            positions_detail.append(position_detail)

            # Aggregate
            greeks_agg["delta"] += position_detail["delta"]
            greeks_agg["gamma"] += position_detail["gamma"]
            greeks_agg["theta"] += position_detail["theta"]
            greeks_agg["vega"] += position_detail["vega"]
            greeks_agg["rho"] += position_detail["rho"]

        return {
            "positions": positions_detail,
            "aggregate_greeks": greeks_agg,
            "portfolio_delta": greeks_agg["delta"],
            "portfolio_theta": greeks_agg["theta"],  # Daily P&L from time decay
            "portfolio_vega": greeks_agg["vega"],  # Sensitivity to 1% vol change
        }


def calculate_option_price_simple(
    spot: float, strike: float, time_years: float, volatility: float, rate: float = 0.04
) -> Tuple[float, float]:
    """Quick call and put price estimate."""
    # Simplified BS
    d1 = (np.log(spot / strike) + (rate + 0.5 * volatility**2) * time_years) / (
        volatility * np.sqrt(time_years)
    )
    d2 = d1 - volatility * np.sqrt(time_years)

    cdf_d1 = 0.5 * (1 + np.tanh(0.797 * d1))
    cdf_d2 = 0.5 * (1 + np.tanh(0.797 * d2))

    call = spot * cdf_d1 - strike * np.exp(-rate * time_years) * cdf_d2
    put = strike * np.exp(-rate * time_years) * (1 - cdf_d2) - spot * (1 - cdf_d1)

    return float(call), float(put)
