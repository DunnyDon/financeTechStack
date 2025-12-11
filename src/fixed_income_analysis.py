"""
Fixed Income Analysis Module

Bond tracking and fixed income analytics:
- Bond price and yield calculations
- Yield curve analysis
- Duration and convexity
- Credit spread monitoring
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class BondMetrics:
    """Fixed income security metrics."""

    yield_to_maturity: float
    price: float
    duration: float
    convexity: float
    modified_duration: float


class FixedIncomeAnalysis:
    """Analyze fixed income securities and portfolios."""

    @staticmethod
    def calculate_bond_price(
        face_value: float,
        coupon_rate: float,
        years_to_maturity: float,
        yield_to_maturity: float,
        payments_per_year: int = 2,
    ) -> float:
        """
        Calculate bond price using present value of cash flows.

        Args:
            face_value: Par value of bond
            coupon_rate: Annual coupon rate
            years_to_maturity: Years until maturity
            yield_to_maturity: YTM (discount rate)
            payments_per_year: Coupon payment frequency

        Returns:
            Bond price
        """
        coupon_payment = (face_value * coupon_rate) / payments_per_year
        periods = int(years_to_maturity * payments_per_year)
        ytm_period = yield_to_maturity / payments_per_year

        if ytm_period == 0:
            # Zero coupon special case
            return face_value / ((1 + ytm_period) ** periods)

        # PV of coupons
        pv_coupons = coupon_payment * (1 - (1 + ytm_period) ** (-periods)) / ytm_period

        # PV of face value
        pv_face = face_value / ((1 + ytm_period) ** periods)

        return float(pv_coupons + pv_face)

    @staticmethod
    def calculate_ytm_simple(
        current_price: float,
        face_value: float,
        coupon_rate: float,
        years_to_maturity: float,
        payments_per_year: int = 2,
        initial_guess: float = 0.05,
    ) -> float:
        """
        Calculate yield to maturity using Newton-Raphson method.

        Args:
            current_price: Current market price
            face_value: Par value
            coupon_rate: Annual coupon rate
            years_to_maturity: Years to maturity
            payments_per_year: Payment frequency
            initial_guess: Starting YTM guess

        Returns:
            Estimated YTM
        """
        ytm = initial_guess
        max_iterations = 100
        tolerance = 1e-6

        for _ in range(max_iterations):
            price = FixedIncomeAnalysis.calculate_bond_price(
                face_value, coupon_rate, years_to_maturity, ytm, payments_per_year
            )

            price_diff = price - current_price

            if abs(price_diff) < tolerance:
                break

            # Approximate derivative for Newton-Raphson
            derivative_ytm = ytm + 0.0001
            derivative_price = FixedIncomeAnalysis.calculate_bond_price(
                face_value, coupon_rate, years_to_maturity, derivative_ytm, payments_per_year
            )
            price_derivative = (derivative_price - price) / 0.0001

            if abs(price_derivative) < 1e-6:
                break

            ytm -= price_diff / price_derivative

        return float(max(0.0001, ytm))

    @staticmethod
    def calculate_duration(
        face_value: float,
        coupon_rate: float,
        years_to_maturity: float,
        yield_to_maturity: float,
        payments_per_year: int = 2,
    ) -> Tuple[float, float, float]:
        """
        Calculate Macaulay duration, modified duration, and effective duration.

        Args:
            face_value: Par value
            coupon_rate: Coupon rate
            years_to_maturity: Years to maturity
            yield_to_maturity: YTM
            payments_per_year: Payment frequency

        Returns:
            Tuple of (macaulay_duration, modified_duration, effective_duration)
        """
        coupon_payment = (face_value * coupon_rate) / payments_per_year
        periods = int(years_to_maturity * payments_per_year)
        ytm_period = yield_to_maturity / payments_per_year

        if ytm_period == 0:
            ytm_period = 0.0001

        # Calculate PV-weighted cash flows
        pv_weighted_times = 0.0
        total_pv = 0.0

        for t in range(1, periods + 1):
            cf = coupon_payment
            if t == periods:
                cf += face_value

            pv = cf / ((1 + ytm_period) ** t)
            pv_weighted_times += t * pv
            total_pv += pv

        macaulay_duration = (pv_weighted_times / total_pv) / payments_per_year

        modified_duration = macaulay_duration / (1 + ytm_period)

        # Effective duration approximation
        effective_duration = modified_duration

        return float(macaulay_duration), float(modified_duration), float(effective_duration)

    @staticmethod
    def calculate_convexity(
        face_value: float,
        coupon_rate: float,
        years_to_maturity: float,
        yield_to_maturity: float,
        payments_per_year: int = 2,
    ) -> float:
        """
        Calculate bond convexity.

        Args:
            face_value: Par value
            coupon_rate: Coupon rate
            years_to_maturity: Years to maturity
            yield_to_maturity: YTM
            payments_per_year: Payment frequency

        Returns:
            Convexity
        """
        coupon_payment = (face_value * coupon_rate) / payments_per_year
        periods = int(years_to_maturity * payments_per_year)
        ytm_period = yield_to_maturity / payments_per_year

        if ytm_period == 0:
            ytm_period = 0.0001

        # Calculate time-weighted PV
        numerator = 0.0
        total_pv = 0.0

        for t in range(1, periods + 1):
            cf = coupon_payment
            if t == periods:
                cf += face_value

            pv = cf / ((1 + ytm_period) ** t)
            numerator += t * (t + 1) * pv
            total_pv += pv

        convexity = (numerator / (total_pv * ((1 + ytm_period) ** 2))) / (payments_per_year**2)

        return float(convexity)

    @staticmethod
    def estimate_price_change(
        current_price: float, yield_change: float, duration: float, convexity: float
    ) -> Dict[str, float]:
        """
        Estimate bond price change from yield change.

        Args:
            current_price: Current bond price
            yield_change: Change in yield
            duration: Modified duration
            convexity: Bond convexity

        Returns:
            Dict with price change and new price
        """
        # Duration approximation with convexity adjustment
        duration_effect = -duration * yield_change
        convexity_effect = 0.5 * convexity * (yield_change**2)

        total_price_change_pct = duration_effect + convexity_effect
        price_change = current_price * total_price_change_pct
        new_price = current_price + price_change

        return {
            "duration_effect_pct": float(duration_effect * 100),
            "convexity_effect_pct": float(convexity_effect * 100),
            "total_change_pct": float(total_price_change_pct * 100),
            "price_change": float(price_change),
            "new_price": float(new_price),
        }

    @staticmethod
    def build_yield_curve(maturities: List[float], yields: List[float]) -> Dict[str, any]:
        """
        Build and analyze yield curve.

        Args:
            maturities: List of years to maturity
            yields: List of yields

        Returns:
            Yield curve analysis
        """
        if len(maturities) < 2:
            return {}

        maturities_array = np.array(maturities)
        yields_array = np.array(yields)

        # Fit polynomial
        coeffs = np.polyfit(maturities_array, yields_array, 2)
        poly = np.poly1d(coeffs)

        # Calculate curve metrics
        slope = yields_array[-1] - yields_array[0]
        is_inverted = slope < 0

        return {
            "maturities": list(maturities),
            "yields": list(yields),
            "slope": float(slope),
            "inverted": is_inverted,
            "curve_type": "inverted" if is_inverted else "normal",
        }

    @staticmethod
    def calculate_credit_spread(bond_yield: float, risk_free_yield: float) -> float:
        """
        Calculate credit spread (OAS approximation).

        Args:
            bond_yield: Bond YTM
            risk_free_yield: Risk-free rate

        Returns:
            Credit spread in basis points
        """
        spread = (bond_yield - risk_free_yield) * 10000  # Convert to bps
        return float(spread)


def analyze_bond_position(
    current_price: float,
    face_value: float,
    coupon_rate: float,
    years_to_maturity: float,
    quantity: int = 1,
) -> Dict[str, float]:
    """Analyze complete bond position."""
    ytm = FixedIncomeAnalysis.calculate_ytm_simple(current_price, face_value, coupon_rate, years_to_maturity)

    mac_dur, mod_dur, eff_dur = FixedIncomeAnalysis.calculate_duration(
        face_value, coupon_rate, years_to_maturity, ytm
    )

    convexity = FixedIncomeAnalysis.calculate_convexity(face_value, coupon_rate, years_to_maturity, ytm)

    return {
        "ytm": ytm,
        "duration": mod_dur,
        "convexity": convexity,
        "current_price": current_price,
        "price_if_rates_up_100bps": FixedIncomeAnalysis.estimate_price_change(current_price, 0.01, mod_dur, convexity)[
            "new_price"
        ],
        "price_if_rates_down_100bps": FixedIncomeAnalysis.estimate_price_change(
            current_price, -0.01, mod_dur, convexity
        )["new_price"],
    }
