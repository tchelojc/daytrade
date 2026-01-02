# flux_on/project/config.py
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List

class TradeType(Enum):
    """Tipos de operações no day trade com todos os cenários cobertos."""
    # --- Operações Básicas ---
    LONG = "Compra (Long)"
    SHORT = "Venda (Short)"
    STOP_LONG = "Stop Loss (Long)"
    STOP_SHORT = "Stop Loss (Short)"
    TAKE_PROFIT_LONG = "Take Profit (Long)"
    TAKE_PROFIT_SHORT = "Take Profit (Short)"
    
    # --- Estratégias ---
    BREAKOUT = "Operação por Rompimento"
    REVERSAL = "Operação por Reversão"
    PULLBACK = "Operação por Pullback"
    SCALPING = "Scalping"
    MOMENTUM = "Momentum Trading"
    
    # --- Hedges ---
    HEDGE = "Proteção (Hedge)"  # ADICIONE ESTA LINHA
    HEDGE_LONG = "Hedge para Posição Long"
    HEDGE_SHORT = "Hedge para Posição Short"
    PAIR_TRADING = "Pair Trading"
    
    # --- Métodos auxiliares ---
    @classmethod
    def get_opposite(cls, trade_type):
        """Retorna o tipo de operação oposta para estratégias de hedge"""
        opposites = {
            cls.LONG: cls.SHORT,
            cls.SHORT: cls.LONG,
            cls.BREAKOUT: cls.REVERSAL,
            cls.STOP_LONG: cls.TAKE_PROFIT_LONG,
            cls.STOP_SHORT: cls.TAKE_PROFIT_SHORT
        }
        return opposites.get(trade_type)
    
    @classmethod
    def is_directional_type(cls, trade_type):
        """Verifica se é uma operação direcional (long/short)"""
        return trade_type in [cls.LONG, cls.SHORT]
    
    @classmethod
    def is_protection_type(cls, trade_type):
        """Verifica se é uma operação de proteção"""
        return trade_type in [cls.STOP_LONG, cls.STOP_SHORT, cls.HEDGE_LONG, cls.HEDGE_SHORT]

class MarketState(Enum):
    """
    Representa o estado do mercado, uma medida da sua volatilidade e tendência.
    - ESTAVEL: Tendência definida, baixa volatilidade.
    - TRANSICAO: Mudança de tendência, momento de alerta.
    - CAOTICO: Alta volatilidade, sem tendência clara.
    - TENDENCIA_ALTA: Mercado em alta consistente.
    - TENDENCIA_BAIXA: Mercado em baixa consistente.
    """
    ESTAVEL = "Estável"
    TRANSICAO = "Transição"
    CAOTICO = "Caótico"
    TENDENCIA_ALTA = "Tendência de Alta"
    TENDENCIA_BAIXA = "Tendência de Baixa"

@dataclass
class AssetCondition:
    """
    Representa uma fotografia do estado atual do ativo.
    Adicione o atributo 'asset' para identificar o ativo sendo analisado
    """
    asset: str = "IBOV"  # Valor padrão ou ajuste conforme necessário
    price: float = 0.0
    volume: float = 0.0
    rsi: float = 50.0
    macd: float = 0.0
    bollinger_band: Dict[str, float] = field(default_factory=lambda: {"upper": 0, "middle": 0, "lower": 0})
    market_context: List[str] = field(default_factory=list)

@dataclass
class QuantumTrade:
    """Representa uma operação individual com todos os seus atributos."""
    trade_type: TradeType
    amount: float
    entry_price: float
    target_price: float
    stop_loss: float
    probability: float
    risk_reward: float
    ev: float = 0.0  # Expected Value

@dataclass
class TradePortfolio:
    """
    Armazena o portfólio de operações, representando a estratégia completa.
    - core_trades: Operações principais (60% do capital).
    - multi_trades: Combinações estratégicas (31% do capital).
    - dynamic_trades: Ajustes dinâmicos (9% do capital).
    """
    capital: float
    core_trades: Dict[str, QuantumTrade] = field(default_factory=dict)  # key = asset
    multi_trades: list = field(default_factory=list)
    dynamic_trades: Dict[str, QuantumTrade] = field(default_factory=dict)

class TradingBias(Enum):
    """Vieses cognitivos comuns no trading."""
    OVERCONFIDENCE = "Excesso de Confiança"
    LOSS_AVERSION = "Aversão à Perda"
    HERD_BEHAVIOR = "Efeito Manada"
    ANCHORING = "Ancoragem"
    RECENCY_BIAS = "Viés da Recenticidade"

@dataclass 
class TraderProfile:
    """
    Perfil de ajustes comportamentais para complementar a modelagem matemática
    """
    asset_weights: Dict[str, float] = field(default_factory=lambda: {
        "IBOV": 1.15,
        "DOLAR": 1.20,
        "ACAO_INDIVIDUAL": 1.10,
        "CRIPTO": 0.95
    })
    
    context_factors: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'FED_MEETING': {"DOLAR": 1.25},
        'RESULTS_SEASON': {"ACAO_INDIVIDUAL": 1.30},
        'BITCOIN_HALVING': {"CRIPTO": 1.40}
    })

class TimeFrame(Enum):
    """Timeframes para análise do mercado"""
    M1 = "1 Minuto"
    M5 = "5 Minutos"
    M15 = "15 Minutos"
    M30 = "30 Minutos"
    H1 = "1 Hora"
    D1 = "1 Dia"

class RiskLevel(Enum):
    """Níveis de risco para operações"""
    CONSERVADOR = "Conservador"
    MODERADO = "Moderado"
    AGRESSIVO = "Agressivo"
    HEDGE = "Proteção"