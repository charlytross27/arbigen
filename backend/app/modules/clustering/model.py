"""K-Means pequeño y determinista; sin I/O ni dependencias de proveedor."""

from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from math import dist, log1p, sqrt
from statistics import mean, median
from typing import Sequence

from app.modules.clustering.domain import ClusterExample, ClusterReport, ClusterSegment
from app.modules.etl.domain import AnalyticalProduct
from app.modules.etl.pipeline import COUNTRY_CURRENCY


MIN_PRODUCTS = 8
MIN_DISTINCT_PRICES = 4
MIN_SILHOUETTE = 0.20
MIN_RELATIVE_PRICE_SPREAD = Decimal("0.15")
MAX_OUTLIER_FRACTION = Decimal("0.10")
MATERIAL_WEIGHT = 0.35
MODEL_VERSION = "price-material-kmeans-v1"


def _two(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _vectorize(products: Sequence[AnalyticalProduct]) -> list[tuple[float, ...]]:
    prices = [log1p(float(product.price)) for product in products]
    average = mean(prices)
    scale = sqrt(mean([(price - average) ** 2 for price in prices]))
    materials = [product.attributes.get("material_hint") or "sin pista" for product in products]
    counts = Counter(materials)
    materials = [material if counts[material] >= 2 else "otras pistas" for material in materials]
    categories = sorted(set(materials)) if len(set(materials)) > 1 else []
    return [((price - average) / scale, *(MATERIAL_WEIGHT * (material == category) for category in categories))
            for price, material in zip(prices, materials)]


def _squared(left: Sequence[float], right: Sequence[float]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right))


def _initial_centers(vectors: Sequence[tuple[float, ...]], k: int, anchor: int) -> list[tuple[float, ...]]:
    centers = [vectors[anchor]]
    for _ in range(1, k):
        next_index = max(range(len(vectors)), key=lambda index: (min(_squared(vectors[index], center) for center in centers), -index))
        centers.append(vectors[next_index])
    return centers


def _fit(vectors: Sequence[tuple[float, ...]], k: int, anchor: int) -> tuple[list[int], list[tuple[float, ...]], float] | None:
    centers = _initial_centers(vectors, k, anchor)
    if len(set(centers)) < k:
        return None
    for _ in range(50):
        labels = [min(range(k), key=lambda group: (_squared(vector, centers[group]), group)) for vector in vectors]
        groups = [[vector for vector, label in zip(vectors, labels) if label == group] for group in range(k)]
        if any(not group for group in groups):
            return None
        next_centers = [tuple(mean(coordinates) for coordinates in zip(*group)) for group in groups]
        if all(_squared(old, new) < 1e-12 for old, new in zip(centers, next_centers)):
            centers = next_centers
            break
        centers = next_centers
    labels = [min(range(k), key=lambda group: (_squared(vector, centers[group]), group)) for vector in vectors]
    if any(labels.count(group) < 2 for group in range(k)):
        return None
    inertia = sum(_squared(vector, centers[label]) for vector, label in zip(vectors, labels))
    return labels, centers, inertia


def _silhouette(vectors: Sequence[tuple[float, ...]], labels: Sequence[int], k: int) -> float:
    distances = [[dist(left, right) for right in vectors] for left in vectors]
    values = []
    for index, group in enumerate(labels):
        own = [other for other, label in enumerate(labels) if label == group and other != index]
        within = mean(distances[index][other] for other in own)
        nearest = min(mean(distances[index][other] for other, label in enumerate(labels) if label == candidate)
                      for candidate in range(k) if candidate != group)
        denominator = max(within, nearest)
        values.append((nearest - within) / denominator if denominator else 0.0)
    return mean(values)


def _without_rare_outliers(products: Sequence[AnalyticalProduct]) -> tuple[list[AnalyticalProduct], int]:
    """Regla de Tukey sobre precio; solo retira una cola pequeña y deja muestra suficiente."""
    count = len(products)
    if count < MIN_PRODUCTS + 1:
        return list(products), 0
    q1 = median(product.price for product in products[:count // 2])
    q3 = median(product.price for product in products[(count + 1) // 2:])
    iqr = q3 - q1
    if iqr <= 0:
        return list(products), 0
    lower = q1 - Decimal("1.5") * iqr
    upper = q3 + Decimal("1.5") * iqr
    retained = [product for product in products if lower <= product.price <= upper]
    excluded = count - len(retained)
    if not excluded or len(retained) < MIN_PRODUCTS or Decimal(excluded) / count > MAX_OUTLIER_FRACTION:
        return list(products), 0
    return retained, excluded


def cluster_products(*, country: str, products: Sequence[AnalyticalProduct]) -> ClusterReport:
    if country not in COUNTRY_CURRENCY:
        raise ValueError("País no admitido para clustering.")
    currency = COUNTRY_CURRENCY[country]
    if any(product.currency != currency or not product.price.is_finite() or product.price < 0 for product in products):
        raise ValueError("El dataset de clustering contiene precios o monedas inválidos.")
    ordered = sorted(products, key=lambda product: (product.price, product.external_id, product.title))
    product_count = len(ordered)
    ordered, excluded_outlier_count = _without_rare_outliers(ordered)
    count = len(ordered)
    if count < MIN_PRODUCTS or len({product.price for product in ordered}) < MIN_DISTINCT_PRICES:
        return ClusterReport(country, currency, "insufficient_data", product_count, count, excluded_outlier_count,
                             None, None, (), "Para formar grupos necesitamos al menos 8 productos con precio y 4 precios diferentes.")
    price_median = median(product.price for product in ordered)
    if (ordered[-1].price - ordered[0].price) / max(price_median, Decimal(1)) < MIN_RELATIVE_PRICE_SPREAD:
        return ClusterReport(country, currency, "no_separation", product_count, count, excluded_outlier_count, None, None, (),
                             "Los precios de esta muestra se parecen demasiado para formar grupos útiles.")

    vectors = _vectorize(ordered)
    best: tuple[float, int, list[int], list[tuple[float, ...]]] | None = None
    for k in range(2, min(4, count // 2) + 1):
        candidates = [_fit(vectors, k, anchor) for anchor in (0, count // 2, count - 1)]
        fitted = min((result for result in candidates if result is not None), key=lambda result: result[2], default=None)
        if fitted is None:
            continue
        labels, centers, _ = fitted
        score = _silhouette(vectors, labels, k)
        if score >= MIN_SILHOUETTE and (best is None or (score, -k) > (best[0], -best[1])):
            best = score, k, labels, centers
    if best is None:
        return ClusterReport(country, currency, "no_separation", product_count, count, excluded_outlier_count, None, None, (),
                             "No se encontraron grupos suficientemente separados y con al menos 2 productos cada uno.")

    score, k, labels, centers = best
    groups = [[index for index, label in enumerate(labels) if label == group] for group in range(k)]
    ranked = sorted(range(k), key=lambda group: (median(ordered[index].price for index in groups[group]), min(groups[group])))
    ranked_medians = [median(ordered[index].price for index in groups[group]) for group in ranked]
    price_tiers_distinct = (ranked_medians[-1] - ranked_medians[0]) / max(price_median, Decimal(1)) >= Decimal("0.05")
    segments = []
    for number, group in enumerate(ranked, start=1):
        members = groups[group]
        prices = [ordered[index].price for index in members]
        hints = dict(sorted(Counter(ordered[index].attributes["material_hint"] for index in members
                                    if ordered[index].attributes.get("material_hint")).items()))
        tier = ("Precio bajo" if number == 1 else "Precio alto" if number == k else "Precio intermedio") if price_tiers_distinct else "Grupo de productos"
        common = Counter(hints).most_common(1)
        label = f"{tier} · {common[0][0]}" if common and common[0][1] > len(members) / 2 else tier
        examples = sorted(members, key=lambda index: (_squared(vectors[index], centers[group]), ordered[index].external_id))[:3]
        segments.append(ClusterSegment(
            number, label, len(members), _two(Decimal(len(members)) / count * 100),
            min(prices), max(prices), _two(mean(prices)), _two(median(prices)), hints,
            tuple(ClusterExample(ordered[index].external_id, ordered[index].title, ordered[index].price) for index in examples),
        ))
    return ClusterReport(country, currency, "ready", product_count, count, excluded_outlier_count,
                         k, _two(score), tuple(segments), None)
