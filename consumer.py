"""
Modulo del Consumidor de escenarios.

Este modulo contiene la clase ConsumidorEscenarios que se encarga de:
- Leer el modelo de la cola de modelo (una vez)
- Obtener escenarios de la cola de escenarios
- Ejecutar el modelo con cada escenario
- Publicar resultados en la cola de resultados
"""

import json
import time
import pika
from typing import Optional, Dict
from model_parser import Modelo
from message_handler import Consumidor, Publicador
import config


class ConsumidorEscenarios:
    """
    Clase que representa un consumidor de escenarios.
    
    El consumidor lee escenarios de la cola, ejecuta el modelo
    y publica los resultados.
    """
    
    def __init__(self, consumer_id: str = "consumer_1"):
        """
        Inicializa el consumidor.
        
        Args:
            consumer_id: Identificador unico del consumidor
        """
        self.consumer_id = consumer_id
        self.modelo = None
        self.modelo_cargado = False
        self.publicador = None
        self.escenarios_procesados = 0
        self.resultados_publicados = 0
        self.tiempo_inicio = None
    
    def inicializar_publicador(self):
        """
        Inicializa el publicador para enviar resultados.
        """
        self.publicador = Publicador()
    
    def cargar_modelo_desde_cola(self):
        """
        Carga el modelo desde la cola de modelo.
        
        Esta funcion se ejecuta una sola vez al inicio.
        Lee el modelo de la cola y lo almacena en memoria.
        """
        if self.modelo_cargado:
            return
        
        print(f"[{self.consumer_id}] Esperando modelo en la cola...")
        
        # Crear un consumidor temporal para leer el modelo
        consumidor_modelo = Consumidor(config.COLA_MODELO)
        
        def callback_modelo(ch, method, properties, body):
            """
            Callback que se ejecuta cuando llega el modelo.
            """
            try:
                modelo_data = json.loads(body)
                self.modelo = Modelo.deserializar(modelo_data)
                self.modelo_cargado = True
                print(f"[{self.consumer_id}] Modelo cargado: {self.modelo.funcion}")
                print(f"[{self.consumer_id}] Variables: {list(self.modelo.variables.keys())}")
                
                # Confirmar que se recibio el mensaje
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
                # Detener el consumo despues de recibir el modelo
                ch.stop_consuming()
            except Exception as e:
                print(f"[{self.consumer_id}] Error al cargar modelo: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        # Consumir un solo mensaje (el modelo)
        consumidor_modelo.channel.basic_qos(prefetch_count=1)
        consumidor_modelo.channel.basic_consume(
            queue=config.COLA_MODELO,
            on_message_callback=callback_modelo,
            auto_ack=False
        )
        
        # Esperar hasta recibir el modelo (con timeout)
        try:
            consumidor_modelo.channel.start_consuming()
        except KeyboardInterrupt:
            consumidor_modelo.channel.stop_consuming()
        
        consumidor_modelo.cerrar()
    
    def procesar_escenario(self, escenario_data: Dict) -> Dict:
        """
        Procesa un escenario ejecutando el modelo.
        
        Args:
            escenario_data: Diccionario con los datos del escenario
            
        Returns:
            Diccionario con el resultado de la ejecucion
        """
        if not self.modelo:
            raise ValueError("El modelo no ha sido cargado")
        
        escenario_id = escenario_data.get('id')
        valores = escenario_data.get('valores', {})
        
        # Ejecutar el modelo con los valores del escenario
        resultado = self.modelo.ejecutar(valores)
        
        return {
            'consumer_id': self.consumer_id,
            'escenario_id': escenario_id,
            'valores': valores,
            'resultado': resultado,
            'timestamp': time.time()
        }
    
    def callback_escenario(self, ch, method, properties, body):
        """
        Callback que se ejecuta cuando llega un escenario.
        
        Args:
            ch: Canal de RabbitMQ
            method: Metodo de entrega
            properties: Propiedades del mensaje
            body: Cuerpo del mensaje
        """
        """
        Callback robusto que reconecta si el publicador se desconectó.
        """
        try:
            # Parsear el escenario
            escenario_data = json.loads(body)
            
            # Procesar el escenario
            resultado = self.procesar_escenario(escenario_data)
            
            # --- BLOQUE DE RECONEXIÓN ---
            try:
                # Intentar publicar
                self.publicador.publicar_resultado(resultado)
            except (pika.exceptions.AMQPConnectionError, pika.exceptions.StreamLostError, OSError):
                print(f"[{self.consumer_id}] Conexión de publicación perdida. Reconectando...")
                # Reiniciar el publicador
                self.publicador = Publicador()
                # Reintentar publicar
                self.publicador.publicar_resultado(resultado)
            # ----------------------------
            
            self.escenarios_procesados += 1
            self.resultados_publicados += 1
            
            # Mostrar progreso cada 10 escenarios
            if self.escenarios_procesados % 10 == 0:
                print(f"[{self.consumer_id}] Escenarios procesados: {self.escenarios_procesados}")
            
            # Confirmar mensaje
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            print(f"[{self.consumer_id}] Error crítico procesando escenario: {e}")
            # IMPORTANTE: No confirmar (ack) si falló, para que otro worker lo tome
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def iniciar_consumo(self):
        """
        Inicia el consumo de escenarios de la cola.
        """
        if not self.modelo_cargado:
            raise ValueError("El modelo debe ser cargado primero")
        
        if not self.publicador:
            raise ValueError("El publicador debe ser inicializado primero")
        
        print(f"[{self.consumer_id}] Iniciando consumo de escenarios...")
        
        # Crear consumidor para escenarios
        consumidor_escenarios = Consumidor(config.COLA_ESCENARIOS)
        
        # Configurar el callback
        consumidor_escenarios.channel.basic_qos(prefetch_count=1)
        consumidor_escenarios.channel.basic_consume(
            queue=config.COLA_ESCENARIOS,
            on_message_callback=self.callback_escenario,
            auto_ack=False
        )
        
        self.tiempo_inicio = time.time()
        
        try:
            consumidor_escenarios.channel.start_consuming()
        except KeyboardInterrupt:
            print(f"\n[{self.consumer_id}] Deteniendo consumo...")
            consumidor_escenarios.channel.stop_consuming()
        
        consumidor_escenarios.cerrar()
    
    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene las estadisticas del consumidor.
        
        Returns:
            Diccionario con las estadisticas
        """
        tiempo_transcurrido = 0
        if self.tiempo_inicio:
            tiempo_transcurrido = time.time() - self.tiempo_inicio
        
        return {
            'consumer_id': self.consumer_id,
            'escenarios_procesados': self.escenarios_procesados,
            'resultados_publicados': self.resultados_publicados,
            'tiempo_transcurrido': tiempo_transcurrido,
            'modelo_cargado': self.modelo_cargado
        }
    
    def ejecutar(self):
        """
        Ejecuta el proceso completo del consumidor.
        
        Este metodo orquesta todas las operaciones:
        1. Inicializa el publicador
        2. Carga el modelo desde la cola
        3. Inicia el consumo de escenarios
        """
        try:
            # Inicializar publicador
            self.inicializar_publicador()
            
            # Cargar modelo
            self.cargar_modelo_desde_cola()
            
            # Iniciar consumo de escenarios
            self.iniciar_consumo()
            
        except Exception as e:
            print(f"[{self.consumer_id}] Error en el consumidor: {e}")
            raise
        finally:
            if self.publicador:
                self.publicador.cerrar()


def main():
    """
    Funcion principal para ejecutar el consumidor desde la linea de comandos.
    """
    import sys
    
    consumer_id = sys.argv[1] if len(sys.argv) > 1 else "consumer_1"
    
    consumidor = ConsumidorEscenarios(consumer_id)
    consumidor.ejecutar()


if __name__ == "__main__":
    main()

