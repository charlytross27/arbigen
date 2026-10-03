"""CSV de Trends con encabezado Day/Week/Month o Time sin geografía interna."""

import csv
import io
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

from app.modules.trends.domain import TrendObservation, TrendSeries, TrendsInputError


COUNTRIES = {"MX": {"mexico", "mx"}, "CO": {"colombia", "co"}, "AR": {"argentina", "ar"}}
DATE_HEADERS = {"day", "week", "month", "time", "date", "dia", "semana", "mes", "fecha"}
MAX_CSV_BYTES = 256 * 1024
MAX_POINTS = 400


def _fold(value: str) -> str:
    return " ".join("".join(character for character in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(character)).split())


def _date(value: str) -> date:
    first = value.strip().split(" - ", 1)[0].strip()
    if re.fullmatch(r"\d{4}-\d{2}", first):
        first += "-01"
    try:
        return date.fromisoformat(first)
    except ValueError as error:
        raise TrendsInputError(f"Fecha inválida en el CSV: {value}.") from error


class GoogleTrendsCsvProvider:
    def load(self, *, query: str, country: str, payload: bytes) -> TrendSeries:
        if country not in COUNTRIES:
            raise TrendsInputError("País no admitido para Google Trends.")
        if not payload or len(payload) > MAX_CSV_BYTES:
            raise TrendsInputError("El CSV debe existir y no superar 256 KB.")
        try:
            content = payload.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise TrendsInputError("El CSV debe estar codificado en UTF-8.") from error
        try:
            rows = list(csv.reader(io.StringIO(content, newline="")))
        except csv.Error as error:
            raise TrendsInputError("El CSV no tiene un formato válido.") from error
        header_index = next((index for index, row in enumerate(rows) if len(row) >= 2 and _fold(row[0]) in DATE_HEADERS), None)
        if header_index is None:
            raise TrendsInputError("No se encontró la tabla de interés por fecha de Google Trends.")
        header = rows[header_index]
        if len(header) != 2:
            raise TrendsInputError("Exporta una sola palabra clave desde Google Trends.")
        match = re.fullmatch(r"\s*(.*?)\s*:\s*\((.*?)\)\s*", header[1])
        term = match.group(1) if match else header[1]
        if _fold(term) != _fold(query):
            raise TrendsInputError(
                f"El CSV corresponde a «{term.strip()[:120]}», pero este análisis es de «{query}». "
                "Importa el CSV de la misma búsqueda o crea un análisis para ese término."
            )
        if match and _fold(match.group(2)) not in COUNTRIES[country]:
            raise TrendsInputError("El país del CSV no coincide con este análisis.")
        source = "google_trends_csv" if match else "google_trends_csv_geo_unverified"

        points: list[TrendObservation] = []
        seen: set[date] = set()
        for row in rows[header_index + 1:]:
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != 2:
                raise TrendsInputError("El CSV contiene columnas adicionales o filas incompletas.")
            point_date = _date(row[0])
            if point_date in seen:
                raise TrendsInputError("El CSV contiene fechas duplicadas.")
            seen.add(point_date)
            raw_value = row[1].strip()
            if raw_value == "<1":
                points.append(TrendObservation(point_date, None, True))
            else:
                try:
                    value = Decimal(raw_value)
                except InvalidOperation as error:
                    raise TrendsInputError(f"Índice inválido en el CSV: {raw_value}.") from error
                if not value.is_finite() or value < 0 or value > 100:
                    raise TrendsInputError("El índice de Google Trends debe estar entre 0 y 100.")
                points.append(TrendObservation(point_date, value))
            if len(points) > MAX_POINTS:
                raise TrendsInputError("El CSV supera el máximo de 400 puntos.")
        if len(points) < 2:
            raise TrendsInputError("El CSV debe contener al menos dos fechas con interés.")
        return TrendSeries(source, tuple(sorted(points, key=lambda point: point.date)))
