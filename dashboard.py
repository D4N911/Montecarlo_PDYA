"""
Modulo del Dashboard visualizador.

Este modulo contiene la clase Dashboard que se encarga de:
- Leer resultados de la cola de resultados
- Mostrar estadisticas en tiempo real
- Visualizar el progreso de la simulacion
- Mostrar estadisticas del productor y consumidores
"""

import json
import time
import threading
from collections import defaultdict, deque
from typing import Dict, List
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                             QTextEdit, QPushButton)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from message_handler import Consumidor
import config


class ResultadoReceiver(QObject):
    """
    Clase para recibir resultados de RabbitMQ en un hilo separado.
    
    Esta clase se comunica con el dashboard mediante señales de PyQt5.
    """
    
    resultado_recibido = pyqtSignal(dict)
    estadisticas_actualizadas = pyqtSignal(dict)
    
    def __init__(self):
        """
        Inicializa el receptor de resultados.
        """
        super().__init__()
        self.consumidor = None
        self.hilo = None
        self.ejecutando = False
        self.resultados = []
        self.estadisticas_consumidores = defaultdict(lambda: {
            'escenarios_procesados': 0,
            'resultados_publicados': 0
        })
    
    def iniciar(self):
        """
        Inicia el consumo de resultados en un hilo separado.
        """
        if self.ejecutando:
            return
        
        self.ejecutando = True
        self.hilo = threading.Thread(target=self._consumir_resultados, daemon=True)
        self.hilo.start()
    
    def detener(self):
        """
        Detiene el consumo de resultados.
        """
        self.ejecutando = False
        if self.consumidor:
            try:
                self.consumidor.channel.stop_consuming()
            except:
                pass
    
    def _consumir_resultados(self):
        """
        Metodo que se ejecuta en el hilo para consumir resultados.
        """
        try:
            self.consumidor = Consumidor(config.COLA_RESULTADOS)
            
            def callback_resultado(ch, method, properties, body):
                """
                Callback que se ejecuta cuando llega un resultado.
                """
                try:
                    resultado = json.loads(body)
                    self.resultados.append(resultado)
                    
                    # Actualizar estadisticas del consumidor
                    consumer_id = resultado.get('consumer_id', 'unknown')
                    self.estadisticas_consumidores[consumer_id]['escenarios_procesados'] += 1
                    self.estadisticas_consumidores[consumer_id]['resultados_publicados'] += 1
                    
                    # Emitir señal con el resultado
                    self.resultado_recibido.emit(resultado)
                    
                    # Emitir señal con estadisticas actualizadas
                    stats = {
                        'total_resultados': len(self.resultados),
                        'consumidores': dict(self.estadisticas_consumidores)
                    }
                    self.estadisticas_actualizadas.emit(stats)
                    
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    print(f"Error al procesar resultado: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            self.consumidor.channel.basic_qos(prefetch_count=10)
            self.consumidor.channel.basic_consume(
                queue=config.COLA_RESULTADOS,
                on_message_callback=callback_resultado,
                auto_ack=False
            )
            
            print("Dashboard: Iniciando consumo de resultados...")
            
            while self.ejecutando:
                try:
                    self.consumidor.connection.process_data_events(time_limit=1)
                except Exception as e:
                    if self.ejecutando:
                        print(f"Error al procesar eventos: {e}")
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error en el receptor de resultados: {e}")
        finally:
            if self.consumidor:
                try:
                    self.consumidor.channel.stop_consuming()
                except:
                    pass
                self.consumidor.cerrar()


class GraficoResultados(FigureCanvas):
    """
    Widget que muestra un grafico de los resultados en tiempo real.
    """
    
    def __init__(self, parent=None):
        """
        Inicializa el grafico.
        """
        self.fig = Figure(figsize=(10, 6))
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.resultados = deque(maxlen=1000)  # Mantener ultimos 1000 resultados
        self.tiempos = deque(maxlen=1000)
        self.tiempo_inicio = time.time()
        
        self.ax.set_xlabel('Tiempo (segundos)')
        self.ax.set_ylabel('Resultado')
        self.ax.set_title('Resultados de la Simulacion en Tiempo Real')
        self.ax.grid(True)
        
        self.line, = self.ax.plot([], [], 'b-', alpha=0.6)
        self.fig.tight_layout()
    
    def agregar_resultado(self, resultado: float):
        """
        Agrega un nuevo resultado al grafico.
        
        Args:
            resultado: Valor del resultado
        """
        tiempo_actual = time.time() - self.tiempo_inicio
        self.resultados.append(resultado)
        self.tiempos.append(tiempo_actual)
        
        if len(self.resultados) > 0:
            self.line.set_data(list(self.tiempos), list(self.resultados))
            self.ax.relim()
            self.ax.autoscale_view()
            self.draw()


class GraficoHistograma(FigureCanvas):
    """
    Widget que muestra un histograma de los resultados.
    """
    
    def __init__(self, parent=None):
        """
        Inicializa el histograma.
        """
        self.fig = Figure(figsize=(8, 6))
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.resultados = []
        
        self.ax.set_xlabel('Valor del Resultado')
        self.ax.set_ylabel('Frecuencia')
        self.ax.set_title('Distribucion de Resultados')
        self.ax.grid(True, alpha=0.3)
        
        self.fig.tight_layout()
    
    def actualizar(self, resultados: List[float]):
        """
        Actualiza el histograma con nuevos resultados.
        
        Args:
            resultados: Lista de resultados
        """
        if len(resultados) == 0:
            return
        
        self.ax.clear()
        self.ax.hist(resultados, bins=50, edgecolor='black', alpha=0.7)
        self.ax.set_xlabel('Valor del Resultado')
        self.ax.set_ylabel('Frecuencia')
        self.ax.set_title('Distribucion de Resultados')
        self.ax.grid(True, alpha=0.3)
        
        # Mostrar estadisticas
        media = np.mean(resultados)
        desviacion = np.std(resultados)
        self.ax.axvline(media, color='r', linestyle='--', label=f'Media: {media:.2f}')
        self.ax.axvline(media + desviacion, color='g', linestyle='--', alpha=0.5, label=f'±1σ: {desviacion:.2f}')
        self.ax.axvline(media - desviacion, color='g', linestyle='--', alpha=0.5)
        self.ax.legend()
        
        self.draw()


class Dashboard(QMainWindow):
    """
    Ventana principal del dashboard.
    
    Muestra estadisticas en tiempo real de la simulacion Montecarlo.
    """
    
    def __init__(self):
        """
        Inicializa el dashboard.
        """
        super().__init__()
        self.setWindowTitle("Dashboard - Simulacion Montecarlo Distribuida")
        self.setGeometry(100, 100, 1400, 900)
        
        # Receptor de resultados
        self.receptor = ResultadoReceiver()
        self.receptor.resultado_recibido.connect(self.on_resultado_recibido)
        self.receptor.estadisticas_actualizadas.connect(self.on_estadisticas_actualizadas)
        
        # Datos
        self.resultados = []
        self.estadisticas_consumidores = {}
        
        # Inicializar UI
        self._inicializar_ui()
        
        # Timer para actualizar la UI periodicamente
        self.timer = QTimer()
        self.timer.timeout.connect(self.actualizar_ui)
        self.timer.start(1000)  # Actualizar cada segundo
        
        # Iniciar recepcion de resultados
        self.receptor.iniciar()
    
    def _inicializar_ui(self):
        """
        Inicializa la interfaz de usuario.
        """
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        
        layout_principal = QVBoxLayout()
        widget_central.setLayout(layout_principal)
        
        # Titulo
        titulo = QLabel("Dashboard - Simulacion Montecarlo Distribuida")
        titulo.setFont(QFont("Arial", 16, QFont.Bold))
        layout_principal.addWidget(titulo)
        
        # Layout horizontal para estadisticas y graficos
        layout_horizontal = QHBoxLayout()
        
        # Panel izquierdo: Estadisticas
        panel_estadisticas = QWidget()
        layout_estadisticas = QVBoxLayout()
        panel_estadisticas.setLayout(layout_estadisticas)
        
        # Estadisticas generales
        self.label_estadisticas = QLabel("Estadisticas Generales")
        self.label_estadisticas.setFont(QFont("Arial", 12, QFont.Bold))
        layout_estadisticas.addWidget(self.label_estadisticas)
        
        self.texto_estadisticas = QTextEdit()
        self.texto_estadisticas.setReadOnly(True)
        self.texto_estadisticas.setMaximumHeight(150)
        layout_estadisticas.addWidget(self.texto_estadisticas)
        
        # Tabla de consumidores
        self.label_consumidores = QLabel("Estadisticas por Consumidor")
        self.label_consumidores.setFont(QFont("Arial", 12, QFont.Bold))
        layout_estadisticas.addWidget(self.label_consumidores)
        
        self.tabla_consumidores = QTableWidget()
        self.tabla_consumidores.setColumnCount(2)
        self.tabla_consumidores.setHorizontalHeaderLabels(["Consumidor", "Escenarios Procesados"])
        layout_estadisticas.addWidget(self.tabla_consumidores)
        
        layout_horizontal.addWidget(panel_estadisticas, 1)
        
        # Panel derecho: Graficos
        panel_graficos = QWidget()
        layout_graficos = QVBoxLayout()
        panel_graficos.setLayout(layout_graficos)
        
        # Grafico de resultados en tiempo real
        self.grafico_resultados = GraficoResultados()
        layout_graficos.addWidget(self.grafico_resultados)
        
        # Grafico de histograma
        self.grafico_histograma = GraficoHistograma()
        layout_graficos.addWidget(self.grafico_histograma)
        
        layout_horizontal.addWidget(panel_graficos, 2)
        
        layout_principal.addLayout(layout_horizontal)
        
        # Boton para detener
        boton_detener = QPushButton("Detener Dashboard")
        boton_detener.clicked.connect(self.cerrar)
        layout_principal.addWidget(boton_detener)
    
    def on_resultado_recibido(self, resultado: Dict):
        """
        Callback que se ejecuta cuando se recibe un resultado.
        
        Args:
            resultado: Diccionario con el resultado
        """
        valor_resultado = resultado.get('resultado', 0)
        self.resultados.append(valor_resultado)
        self.grafico_resultados.agregar_resultado(valor_resultado)
    
    def on_estadisticas_actualizadas(self, estadisticas: Dict):
        """
        Callback que se ejecuta cuando se actualizan las estadisticas.
        
        Args:
            estadisticas: Diccionario con las estadisticas
        """
        self.estadisticas_consumidores = estadisticas.get('consumidores', {})
    
    def actualizar_ui(self):
        """
        Actualiza la interfaz de usuario con las estadisticas mas recientes.
        """
        # Actualizar estadisticas generales
        total_resultados = len(self.resultados)
        texto = f"Total de Resultados: {total_resultados}\n"
        
        if len(self.resultados) > 0:
            media = np.mean(self.resultados)
            desviacion = np.std(self.resultados)
            minimo = np.min(self.resultados)
            maximo = np.max(self.resultados)
            
            texto += f"Media: {media:.4f}\n"
            texto += f"Desviacion Estandar: {desviacion:.4f}\n"
            texto += f"Minimo: {minimo:.4f}\n"
            texto += f"Maximo: {maximo:.4f}\n"
        
        self.texto_estadisticas.setText(texto)
        
        # Actualizar tabla de consumidores
        self.tabla_consumidores.setRowCount(len(self.estadisticas_consumidores))
        fila = 0
        for consumer_id, stats in self.estadisticas_consumidores.items():
            self.tabla_consumidores.setItem(fila, 0, QTableWidgetItem(str(consumer_id)))
            self.tabla_consumidores.setItem(fila, 1, QTableWidgetItem(str(stats['escenarios_procesados'])))
            fila += 1
        
        # Actualizar histograma
        if len(self.resultados) > 0:
            self.grafico_histograma.actualizar(self.resultados)
    
    def cerrar(self):
        """
        Cierra el dashboard y detiene la recepcion de resultados.
        """
        self.receptor.detener()
        self.close()


def main():
    """
    Funcion principal para ejecutar el dashboard.
    """
    app = QApplication([])
    dashboard = Dashboard()
    dashboard.show()
    app.exec_()


if __name__ == "__main__":
    main()

