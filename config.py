"""
Configuracion del sistema de simulacion Montecarlo distribuida.

Este modulo contiene todas las constantes y configuraciones necesarias
para la comunicacion entre los componentes del sistema.
"""

# Configuracion de RabbitMQ
RABBITMQ_HOST = 'localhost'
RABBITMQ_PORT = 5672
RABBITMQ_USER = 'guest'
RABBITMQ_PASSWORD = 'guest'

# Nombres de las colas
COLA_MODELO = 'cola_modelo'
COLA_ESCENARIOS = 'cola_escenarios'
COLA_RESULTADOS = 'cola_resultados'

# Configuracion de mensajes
EXCHANGE_NAME = 'montecarlo_exchange'
ROUTING_KEY_MODELO = 'modelo'
ROUTING_KEY_ESCENARIO = 'escenario'
ROUTING_KEY_RESULTADO = 'resultado'

# Timeout para la cola de modelo (en segundos)
MODEL_TIMEOUT = 3600  # 1 hora por defecto

# Configuracion de generacion de escenarios
NUM_ESCENARIOS_DEFAULT = 1000

