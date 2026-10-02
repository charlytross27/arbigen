"""Selección temporal de baselines sin imputar datos censurados ni consultar fuentes."""

import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from math import ceil
from statistics import mean
from typing import Literal, Sequence

from app.modules.etl.domain import AnalyticalTrendPoint
from app.modules.forecasting.domain import ForecastPoint, ForecastReport


MODEL_VERSION = "trends-rolling-baselines-v1"
MIN_TRAIN = 8
MIN_ORIGINS = 6
HORIZON = 3
MAX_MAE = 20.0
MIN_BAND = 5.0
Frequency = Literal["daily", "weekly", "monthly"]
Method = Literal["naive", "moving_average_3", "drift", "seasonal_naive"]
RejectedStatus = Literal["insufficient_data", "censored_data", "irregular_series"]


def _two(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _clamp(value: float) -> float:
    return min(100.0, max(0.0, value))


def _advance(start: date, frequency: Frequency, steps: int) -> date:
    if frequency == "daily":
        return start + timedelta(days=steps)
    if frequency == "weekly":
        return start + timedelta(days=7 * steps)
    month = start.month - 1 + steps
    year = start.year + month // 12
    month = month % 12 + 1
    last = calendar.monthrange(year, month)[1]
    anchor_is_month_end = start.day == calendar.monthrange(start.year, start.month)[1]
    return date(year, month, last if anchor_is_month_end else min(start.day, last))


def _frequency(points: Sequence[AnalyticalTrendPoint]) -> Frequency | None:
    for candidate in ("daily", "weekly", "monthly"):
        if all(point.date == _advance(points[0].date, candidate, index) for index, point in enumerate(points)):
            return candidate
    return None


def _predict(values: Sequence[float], method: Method, horizon: int, period: int | None) -> list[float]:
    if method == "naive":
        return [values[-1]] * horizon
    if method == "moving_average_3":
        return [mean(values[-3:])] * horizon
    if method == "drift":
        slope = (values[-1] - values[0]) / (len(values) - 1)
        return [_clamp(values[-1] + slope * step) for step in range(1, horizon + 1)]
    assert period is not None and len(values) >= 2 * period
    return [values[-period + step - 1] for step in range(1, horizon + 1)]


def _rejected(status: RejectedStatus, points: Sequence[AnalyticalTrendPoint],
              used_count: int, reason: str, frequency: Frequency | None = None) -> ForecastReport:
    return ForecastReport(status, len(points), used_count, sum(point.less_than_one for point in points),
                          frequency, None, None, False, None, None, {}, 0, HORIZON, (), reason)


def forecast_trends(points: Sequence[AnalyticalTrendPoint]) -> ForecastReport:
    ordered = sorted(points, key=lambda point: point.date)
    if len({point.date for point in ordered}) != len(ordered):
        raise ValueError("La serie de Trends contiene fechas duplicadas.")
    if any((point.less_than_one and point.value is not None) or
           (not point.less_than_one and (point.value is None or not point.value.is_finite() or not 0 <= point.value <= 100))
           for point in ordered):
        raise ValueError("La serie de Trends contiene índices inválidos.")
    if not ordered:
        return _rejected("insufficient_data", ordered, 0, "Importa primero un CSV de Google Trends.")
    last_censored = max((index for index, point in enumerate(ordered) if point.less_than_one), default=-1)
    usable = ordered[last_censored + 1:]
    if len(usable) < MIN_TRAIN + MIN_ORIGINS + HORIZON - 1:
        status = "censored_data" if last_censored >= 0 else "insufficient_data"
        return _rejected(status, ordered, len(usable),
                         "Se necesitan al menos 16 puntos consecutivos observados después del último valor <1.")
    frequency = _frequency(usable)
    if frequency is None:
        return _rejected("irregular_series", ordered, len(usable),
                         "Las fechas recientes no tienen frecuencia diaria, semanal o mensual sin huecos.")

    values = [float(point.value) for point in usable if point.value is not None]
    period = {"daily": 7, "weekly": 52, "monthly": 12}[frequency]
    seasonal_possible = len(values) >= 2 * period + MIN_ORIGINS + HORIZON - 1
    first_origin = max(MIN_TRAIN, 2 * period) if seasonal_possible else MIN_TRAIN
    origins = list(range(first_origin, len(values) - HORIZON + 1))
    methods: list[Method] = ["naive", "moving_average_3", "drift"]
    if seasonal_possible:
        methods.append("seasonal_naive")
    errors: dict[Method, list[list[float]]] = {}
    for method in methods:
        errors[method] = [[] for _ in range(HORIZON)]
        for end in origins:
            predicted = _predict(values[:end], method, HORIZON, period)
            for step, result in enumerate(predicted):
                errors[method][step].append(abs(result - values[end + step]))
    scores = {method: mean(error for horizon_errors in errors[method] for error in horizon_errors)
              for method in methods}
    candidate_mae = {method: _two(score) for method, score in scores.items()}
    selected = min(methods, key=lambda method: (scores[method], methods.index(method)))
    if scores[selected] > MAX_MAE:
        return ForecastReport("low_skill", len(ordered), len(usable), sum(point.less_than_one for point in ordered),
                              frequency, None, None, False, _two(scores[selected]), _two(scores["naive"]), candidate_mae,
                              len(origins), HORIZON, (),
                              "El error medio de validación supera 20 puntos del índice; no se publica un pronóstico.")

    predicted = _predict(values, selected, HORIZON, period)
    intervals = []
    for step in range(HORIZON):
        sorted_errors = sorted(errors[selected][step])
        empirical_error = sorted_errors[ceil(0.8 * len(sorted_errors)) - 1]
        band = max(MIN_BAND, empirical_error)
        value = _clamp(predicted[step])
        intervals.append(ForecastPoint(
            _advance(usable[0].date, frequency, len(usable) + step),
            _two(value), _two(_clamp(value - band)), _two(_clamp(value + band)),
        ))
    recent_change = mean(values[-3:]) - mean(values[-6:-3])
    direction = "creciente" if recent_change > 5 else "decreciente" if recent_change < -5 else "estable"
    return ForecastReport(
        "ready", len(ordered), len(usable), sum(point.less_than_one for point in ordered),
        frequency, selected, direction,
        selected == "seasonal_naive" and scores[selected] < scores["naive"] * 0.9,
        _two(scores[selected]), _two(scores["naive"]), candidate_mae, len(origins), HORIZON, tuple(intervals), None,
    )
