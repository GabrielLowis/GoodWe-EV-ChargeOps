### Valores permitidos nas colunas de status. ###

# Sao mesmos valores aparecem nas restrições CHECK da migration 0001, então o banco recusa qualquer valor fora desta lista. 
# Como StrEnum herda de str, os membros podem ser gravados e comparados diretamente com as colunas de texto.

# Cria enumeracoes em string
from enum import StrEnum

# Verifica quem é morador ou sindico
class UserRole(StrEnum):
    RESIDENT = "resident"  
    MANAGER = "manager"  
    
# Separa as classes, reservada, em uso, encerrada,cancelada, ou nao apresentou
class ReservationStatus(StrEnum):
    ACTIVE = "active"  
    IN_USE = "in_use" 
    COMPLETED = "completed"  
    CANCELLED = "cancelled" 
    NO_SHOW = "no_show"  

# Reservas nesses estados ocupam o conector e bloqueiam novas reservas no mesmo horário.
BLOCKING_RESERVATION_STATUSES = (ReservationStatus.ACTIVE, ReservationStatus.IN_USE)

# NAO TEMOS ACESSO A API #
class DataSource(StrEnum):
    SEMS = "sems"  # API SEMS+ da GoodWe (fonte primária da demo)
    GATEWAY = "gateway"  # gateway local Modbus (contingência)
    SIMULATOR = "simulator"  # simulador do HCA G2

# Classificacao do encerramento - Etapa 4 do sprint 1, 
# No qual esta em progresso, completada, encerrado antes do termino ou interrompida pela falha do sistem
class SessionEndStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed" 
    USER_STOPPED = "user_stopped"  
    SYSTEM_FAILURE = "system_failure" 

# Resultado das validacoes fisicas e para verificar as anomalias
# Verificar se nao foi validado, se pode entrar na fatura, suspeita e precisa de validacao e revisao e nao é cobrada
class ValidationStatus(StrEnum):
    PENDING = "pending"  
    APPROVED = "approved" 
    SUSPENDED = "suspended"  
    REJECTED = "rejected"  

# Atribuicao dos metodos, se ainda nao tem morador, inicio da sessao, rede de seguranca, atribuida pelo sindico
class AttributionMethod(StrEnum):
    UNATTRIBUTED = "unattributed"  
    RESERVATION = "reservation"  
    CARD_CUSTODIAN = "card_custodian"  
    MANUAL = "manual" 

# Faixa de horarios inspirado na tarifa branca da ANEEL
# Fora do pico, intermediaria e no pico
class Band(StrEnum):
    OFF_PEAK = "off_peak"  
    INTERMEDIATE = "intermediate"  
    PEAK = "peak"  

BAND_LABELS_PT = {
    Band.OFF_PEAK: "Fora de ponta",
    Band.INTERMEDIATE: "Intermediário",
    Band.PEAK: "Ponta",
}

# Tipos de taxas
class TaxType(StrEnum):
    ICMS = "icms"
    ISS = "iss"
    IBS = "ibs"
    CBS = "cbs"

# As taxas podem ser recalculadas ou sao imutaveis
class InvoiceStatus(StrEnum):
    OPEN = "open"  
    CLOSED = "closed" 

# Na fila para a revisao do sindico, se esta pendente, aprovada ou recusada
class AnomalyStatus(StrEnum):
    PENDING_REVIEW = "pending_review"  
    APPROVED = "approved"  
    REJECTED = "rejected"  

# Regra de cobranca aplicada a uma sessao. Se houve ociosidade e energia, se foi entregue e se foi registrada com o valor zero
class ChargeRule(StrEnum):
    NORMAL = "normal" 
    USER_STOPPED_NO_IDLE = "user_stopped_no_idle" 
    SYSTEM_FAILURE_NO_CHARGE = "system_failure_no_charge"  
