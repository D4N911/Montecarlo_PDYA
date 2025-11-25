"""
Modulo para manejar la comunicacion con RabbitMQ.

Este modulo proporciona clases para enviar y recibir mensajes
a traves de RabbitMQ de forma encapsulada.
"""

import json
import pika
from typing import Optional, Callable
import config


class ManejadorMensajes:
    """
    Clase base para manejar la comunicacion con RabbitMQ.
    
    Esta clase encapsula la logica de conexion y configuracion
    de RabbitMQ para que las otras clases puedan usarla facilmente.
    """
    
    def __init__(self):
        """
        Inicializa la conexion con RabbitMQ.
        """
        self.connection = None
        self.channel = None
        self._conectar()
    
    def _conectar(self):
        """
        Establece la conexion con RabbitMQ.
        """
        try:
            credentials = pika.PlainCredentials(
                config.RABBITMQ_USER,
                config.RABBITMQ_PASSWORD
            )
            parameters = pika.ConnectionParameters(
                host=config.RABBITMQ_HOST,
                port=config.RABBITMQ_PORT,
                credentials=credentials
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
        except Exception as e:
            raise ConnectionError(f"Error al conectar con RabbitMQ: {e}")
    
    def cerrar(self):
        """
        Cierra la conexion con RabbitMQ.
        """
        if self.connection and not self.connection.is_closed:
            self.connection.close()


class Publicador(ManejadorMensajes):
    """
    Clase para publicar mensajes en las colas de RabbitMQ.
    
    Esta clase se encarga de publicar mensajes en las diferentes
    colas del sistema (modelo, escenarios, resultados).
    """
    
    def __init__(self):
        """
        Inicializa el publicador y declara las colas necesarias.
        """
        super().__init__()
        self._declarar_colas()
    
    def _declarar_colas(self):
        """
        Declara todas las colas que se van a usar en el sistema.
        """
        # Cola de modelo con expiracion
        self.channel.queue_declare(
            queue=config.COLA_MODELO,
            durable=True,
            arguments={
                'x-message-ttl': config.MODEL_TIMEOUT * 1000  # TTL en milisegundos
            }
        )
        
        # Cola de escenarios
        self.channel.queue_declare(
            queue=config.COLA_ESCENARIOS,
            durable=True
        )
        
        # Cola de resultados
        self.channel.queue_declare(
            queue=config.COLA_RESULTADOS,
            durable=True
        )
    
    def publicar_modelo(self, modelo_data: dict):
        """
        Publica el modelo en la cola de modelo.
        
        Args:
            modelo_data: Diccionario con los datos del modelo
        """
        mensaje = json.dumps(modelo_data)
        self.channel.basic_publish(
            exchange='',
            routing_key=config.COLA_MODELO,
            body=mensaje,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Hacer el mensaje persistente
            )
        )
        print(f"Modelo publicado en {config.COLA_MODELO}")
    
    def publicar_escenario(self, escenario: dict, escenario_id: int):
        """
        Publica un escenario en la cola de escenarios.
        
        Args:
            escenario: Diccionario con los valores de las variables
            escenario_id: Identificador unico del escenario
        """
        mensaje = {
            'id': escenario_id,
            'valores': escenario
        }
        mensaje_json = json.dumps(mensaje)
        self.channel.basic_publish(
            exchange='',
            routing_key=config.COLA_ESCENARIOS,
            body=mensaje_json,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Hacer el mensaje persistente
            )
        )
    
    def publicar_resultado(self, resultado: dict):
        """
        Publica un resultado en la cola de resultados.
        
        Args:
            resultado: Diccionario con el resultado de la simulacion
        """
        mensaje_json = json.dumps(resultado)
        self.channel.basic_publish(
            exchange='',
            routing_key=config.COLA_RESULTADOS,
            body=mensaje_json,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Hacer el mensaje persistente
            )
        )
    def purgar_cola_modelo(self):
        """Limpia la cola de modelos para asegurar que solo exista el nuevo."""
        try:
            self.channel.queue_purge(queue=config.COLA_MODELO)
            print(f"Cola {config.COLA_MODELO} purgada.")
        except Exception as e:
            print(f"Advertencia al purgar cola: {e}")


class Consumidor(ManejadorMensajes):
    """
    Clase base para consumir mensajes de las colas de RabbitMQ.
    
    Esta clase proporciona la funcionalidad basica para consumir
    mensajes de una cola especifica.
    """
    
    def __init__(self, nombre_cola: str):
        """
        Inicializa el consumidor para una cola especifica.
        """
        super().__init__()
        self.nombre_cola = nombre_cola

        # Definir argumentos si es la cola de modelo (para coincidir con el Productor)
        args = None
        if nombre_cola == config.COLA_MODELO:
            args = {
                'x-message-ttl': config.MODEL_TIMEOUT * 1000
            }
            
        self.channel.queue_declare(
            queue=nombre_cola, 
            durable=True,
            arguments=args  # faltaba este argumento
        )
    
    def consumir(self, callback: Callable, auto_ack: bool = False):
        """
        Inicia el consumo de mensajes de la cola.
        
        Args:
            callback: Funcion que se ejecutara cuando llegue un mensaje
            auto_ack: Si es True, los mensajes se confirman automaticamente
        """
        self.channel.basic_qos(prefetch_count=1)  # Procesar un mensaje a la vez
        self.channel.basic_consume(
            queue=self.nombre_cola,
            on_message_callback=callback,
            auto_ack=auto_ack
        )
        
        print(f"Esperando mensajes en {self.nombre_cola}. Presiona CTRL+C para salir")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.cerrar()

