"""
Modulo del Productor de escenarios.

Este modulo contiene la clase Productor que se encarga de:
- Leer el modelo desde un archivo de texto
- Generar escenarios unicos
- Publicar el modelo en la cola de modelo
- Publicar escenarios en la cola de escenarios
"""

import time
import json
from typing import Dict
from model_parser import ParserModelo, Modelo
from message_handler import Publicador
import config


class Productor:
    """
    Clase que representa el productor de escenarios.
    
    El productor es responsable de generar escenarios unicos
    a partir de un modelo y publicarlos en RabbitMQ.
    """
    
    def __init__(self, ruta_modelo: str, num_escenarios: int = config.NUM_ESCENARIOS_DEFAULT):
        """
        Inicializa el productor.
        
        Args:
            ruta_modelo: Ruta al archivo de texto con el modelo
            num_escenarios: Numero de escenarios a generar
        """
        self.ruta_modelo = ruta_modelo
        self.num_escenarios = num_escenarios
        self.modelo = None
        self.publicador = None
        self.escenarios_generados = 0
        self.escenarios_publicados = 0
    
    def cargar_modelo(self):
        """
        Carga el modelo desde el archivo de texto.
        """
        print(f"Cargando modelo desde {self.ruta_modelo}...")
        parser = ParserModelo()
        self.modelo = parser.parsear_archivo(self.ruta_modelo)
        print(f"Modelo cargado: {self.modelo.funcion}")
        print(f"Variables: {list(self.modelo.variables.keys())}")
    
    def inicializar_publicador(self):
        """
        Inicializa la conexion con RabbitMQ.
        """
        print("Conectando con RabbitMQ...")
        self.publicador = Publicador()
        print("Conectado exitosamente")
    
    def publicar_modelo(self):
        """
        Publica el modelo en la cola de modelo.
        
        El modelo se publica con un TTL (time to live) que hace que
        expire cuando se carga un nuevo modelo.
        """
        if not self.modelo:
            raise ValueError("El modelo no ha sido cargado")
        
        # Limpiar la cola de modelo antes de publicar el nuevo modelo
        self.publicador.purgar_cola_modelo()
        
        modelo_serializado = self.modelo.serializar()
        self.publicador.publicar_modelo(modelo_serializado)
        print("Modelo publicado en la cola de modelo")
    
    def generar_y_publicar_escenarios(self):
        """
        Genera escenarios unicos y los publica en la cola de escenarios.
        
        Cada escenario tiene un ID unico para poder rastrearlo.
        """
        if not self.modelo:
            raise ValueError("El modelo no ha sido cargado")
        
        if not self.publicador:
            raise ValueError("El publicador no ha sido inicializado")
        
        print(f"Generando {self.num_escenarios} escenarios...")
        
        for i in range(1, self.num_escenarios + 1):
            # Generar un escenario unico
            escenario = self.modelo.generar_escenario()
            
            # Publicar el escenario
            self.publicador.publicar_escenario(escenario, i)
            
            self.escenarios_generados += 1
            self.escenarios_publicados += 1
            
            # Mostrar progreso cada 100 escenarios
            if i % 100 == 0:
                print(f"Escenarios publicados: {i}/{self.num_escenarios}")
        
        print(f"Todos los escenarios han sido publicados ({self.num_escenarios})")
    
    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene las estadisticas del productor.
        
        Returns:
            Diccionario con las estadisticas
        """
        return {
            'escenarios_generados': self.escenarios_generados,
            'escenarios_publicados': self.escenarios_publicados,
            'total_escenarios': self.num_escenarios,
            'progreso': (self.escenarios_publicados / self.num_escenarios * 100) if self.num_escenarios > 0 else 0
        }
    
    def ejecutar(self):
        """
        Ejecuta el proceso completo del productor.
        
        Este metodo orquesta todas las operaciones:
        1. Carga el modelo
        2. Inicializa el publicador
        3. Publica el modelo
        4. Genera y publica los escenarios
        """
        try:
            # Cargar el modelo
            self.cargar_modelo()
            
            # Inicializar la conexion con RabbitMQ
            self.inicializar_publicador()
            
            # Publicar el modelo
            self.publicar_modelo()
            
            # Generar y publicar escenarios
            self.generar_y_publicar_escenarios()
            
            print("\nProductor finalizado exitosamente")
            
        except Exception as e:
            print(f"Error en el productor: {e}")
            raise
        finally:
            if self.publicador:
                self.publicador.cerrar()


def main():
    """
    Funcion principal para ejecutar el productor desde la linea de comandos.
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python producer.py <ruta_modelo> [num_escenarios]")
        sys.exit(1)
    
    ruta_modelo = sys.argv[1]
    num_escenarios = int(sys.argv[2]) if len(sys.argv) > 2 else config.NUM_ESCENARIOS_DEFAULT
    
    productor = Productor(ruta_modelo, num_escenarios)
    productor.ejecutar()


if __name__ == "__main__":
    main()

