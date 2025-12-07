"""
Voting Business Logic für Planning Poker
Enthält Konsens-Prüfung und Voting-Auswertung
"""

from collections import Counter
from typing import List, Tuple, Optional

# Fibonacci-Zahlen für Planning Poker
FIBONACCI = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]


def find_majority_value(vote_values: List[int]) -> Optional[int]:
    """Findet den Mehrheitswert in einer Liste von Votes"""
    if not vote_values:
        return None

    counter = Counter(vote_values)
    most_common = counter.most_common(1)[0]
    return most_common[0]


def calculate_alternative_value(
    vote_values: List[int], highest_value: int
) -> Optional[int]:
    """
    Berechnet den alternativen Wert bei Divergenz

    Logik:
    1. Mehrheitswert (wenn != highest_value und count > 1)
    2. Zweithöchster Wert
    3. None (wenn nur ein einziger Vote oder keine Alternative verfügbar)
    """
    if len(vote_values) <= 1:
        return None

    counter = Counter(vote_values)
    most_common_value = counter.most_common(1)[0][0]

    # Mehrheitswert als Alternative (wenn != höchster und mehr als 1 Stimme)
    if most_common_value != highest_value and counter[most_common_value] > 1:
        return most_common_value

    # Zweithöchster Wert
    sorted_unique = sorted(set(vote_values), reverse=True)
    if len(sorted_unique) >= 2:
        return sorted_unique[1]

    return None


def check_consensus(vote_values: List[int]) -> Tuple[str, Optional[int], Optional[int]]:
    """
    Prüft Konsens und gibt zurück: ("consensus"|"near_consensus"|"divergence", suggested_points, alternative_points)

    Args:
        vote_values: Liste von abgegebenen Punkten

    Returns:
        Tuple aus (consensus_type, suggested_points, alternative_points)
        - consensus: Alle stimmen überein
        - near_consensus: Nur einer weicht um eine Fibonacci-Zahl ab
        - divergence: Keine Einigkeit, höchster Wert + Alternative wird vorgeschlagen
    """
    if not vote_values or len(vote_values) < 1:
        return "divergence", None, None

    unique_values = set(vote_values)

    # Fall 1: Alle gleich
    if len(unique_values) == 1:
        return "consensus", list(unique_values)[0], None

    # Fall 2: Fast-Konsens (nur einer weicht ab, um max 1 Fibonacci-Zahl)
    if len(vote_values) >= 2:
        counter = Counter(vote_values)
        most_common_value, most_common_count = counter.most_common(1)[0]

        # Prüfen ob nur einer abweicht
        if most_common_count == len(vote_values) - 1:
            # Finde den abweichenden Wert
            for value in unique_values:
                if value != most_common_value:
                    outlier = value
                    # Prüfe ob nur eine Fibonacci-Zahl daneben
                    try:
                        idx_majority = FIBONACCI.index(most_common_value)
                        idx_outlier = FIBONACCI.index(outlier)
                        if abs(idx_majority - idx_outlier) == 1:
                            return "near_consensus", most_common_value, None
                    except ValueError:
                        pass

    # Fall 3: Divergenz - höchster Wert + Alternative
    highest_value = max(vote_values)
    alternative_value = calculate_alternative_value(vote_values, highest_value)
    return "divergence", highest_value, alternative_value
