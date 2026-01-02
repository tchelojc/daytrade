# project/utils.py
import numpy as np
from typing import TypeVar, Union

T = TypeVar('T', float, complex, np.ndarray)

def safe_divide(a: float, b: float, default: float = 1.0) -> float:
    """Divisão segura com proteção contra divisão por zero e valores muito pequenos"""
    try:
        if abs(b) < 1e-8:  # Valor extremamente próximo de zero
            return default
        result = a / b
        if not np.isfinite(result):  # Verifica se é infinito ou NaN
            return default
        return result
    except (TypeError, ZeroDivisionError):
        return default

def quantum_superposition(states: list[T], probabilities: list[float]) -> T:
    """Retorna uma superposição quântica dos estados de entrada"""
    if len(states) != len(probabilities):
        raise ValueError("States and probabilities must have same length")
    if not np.isclose(sum(probabilities), 1.0):
        raise ValueError("Probabilities must sum to 1")
    
    # Medição probabilística
    choice = np.random.choice(len(states), p=probabilities)
    return states[choice]