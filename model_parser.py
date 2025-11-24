"""
Modulo para parsear modelos desde archivos de texto.

Este modulo se encarga de leer y parsear archivos de texto que contienen
la definicion de un modelo matematico con sus variables y distribuciones.
"""

import re
import ast
from typing import Dict, List, Tuple
import numpy as np
from scipy import stats


class Variable:
    """
    Clase que representa una variable del modelo con su distribucion de probabilidad.
    
    Atributos:
        nombre: Nombre de la variable
        distribucion: Tipo de distribucion (normal, uniform, exponencial, etc.)
        parametros: Parametros de la distribucion
    """
    
    def __init__(self, nombre: str, distribucion: str, parametros: Dict):
        """
        Inicializa una variable.
        
        Args:
            nombre: Nombre de la variable
            distribucion: Tipo de distribucion
            parametros: Diccionario con los parametros de la distribucion
        """
        self.nombre = nombre
        self.distribucion = distribucion.lower()
        self.parametros = parametros
    
    def generar_valor(self) -> float:
        """
        Genera un valor aleatorio segun la distribucion de la variable.
        
        Returns:
            Valor aleatorio generado
        """
        if self.distribucion == 'normal':
            return np.random.normal(
                self.parametros.get('media', 0),
                self.parametros.get('desviacion', 1)
            )
        elif self.distribucion == 'uniform':
            return np.random.uniform(
                self.parametros.get('min', 0),
                self.parametros.get('max', 1)
            )
        elif self.distribucion == 'exponencial':
            return np.random.exponential(
                self.parametros.get('lambda', 1)
            )
        elif self.distribucion == 'triangular':
            return np.random.triangular(
                self.parametros.get('left', 0),
                self.parametros.get('mode', 0.5),
                self.parametros.get('right', 1)
            )
        else:
            raise ValueError(f"Distribucion no soportada: {self.distribucion}")


class Modelo:
    """
    Clase que representa un modelo matematico completo.
    
    Atributos:
        funcion: Funcion del modelo como string
        variables: Lista de variables del modelo
    """
    
    def __init__(self, funcion: str, variables: List[Variable]):
        """
        Inicializa un modelo.
        
        Args:
            funcion: Funcion del modelo como string
            variables: Lista de variables del modelo
        """
        self.funcion = funcion
        self.variables = {var.nombre: var for var in variables}
    
    def ejecutar(self, valores: Dict[str, float]) -> float:
        """
        Ejecuta el modelo con valores especificos de las variables.
        
        Args:
            valores: Diccionario con los valores de las variables
            
        Returns:
            Resultado de ejecutar el modelo
        """
        # Crear un contexto seguro para evaluar la expresion
        contexto = valores.copy()
        contexto.update({
            'np': np,
            'sin': np.sin,
            'cos': np.cos,
            'exp': np.exp,
            'log': np.log,
            'sqrt': np.sqrt,
            'abs': np.abs,
            'max': np.maximum,
            'min': np.minimum
        })
        
        try:
            # Compilar y evaluar la expresion de forma segura
            codigo_compilado = compile(self.funcion, '<string>', 'eval')
            resultado = eval(codigo_compilado, {"__builtins__": {}}, contexto)
            return float(resultado)
        except Exception as e:
            raise ValueError(f"Error al ejecutar el modelo: {e}")
    
    def generar_escenario(self) -> Dict[str, float]:
        """
        Genera un escenario aleatorio con valores para todas las variables.
        
        Returns:
            Diccionario con los valores generados para cada variable
        """
        escenario = {}
        for nombre, variable in self.variables.items():
            escenario[nombre] = variable.generar_valor()
        return escenario
    
    def serializar(self) -> Dict:
        """
        Serializa el modelo a un diccionario para enviarlo por mensaje.
        
        Returns:
            Diccionario serializado del modelo
        """
        return {
            'funcion': self.funcion,
            'variables': [
                {
                    'nombre': var.nombre,
                    'distribucion': var.distribucion,
                    'parametros': var.parametros
                }
                for var in self.variables.values()
            ]
        }
    
    @staticmethod
    def deserializar(datos: Dict) -> 'Modelo':
        """
        Deserializa un modelo desde un diccionario.
        
        Args:
            datos: Diccionario con los datos del modelo
            
        Returns:
            Instancia de Modelo
        """
        variables = []
        for var_data in datos['variables']:
            variable = Variable(
                var_data['nombre'],
                var_data['distribucion'],
                var_data['parametros']
            )
            variables.append(variable)
        
        return Modelo(datos['funcion'], variables)


class ParserModelo:
    """
    Clase para parsear archivos de texto que contienen definiciones de modelos.
    """
    
    @staticmethod
    def parsear_archivo(ruta_archivo: str) -> Modelo:
        """
        Parsea un archivo de texto y crea un objeto Modelo.
        
        El formato del archivo debe ser:
        FUNCION: expresion_matematica
        VARIABLES:
        nombre_variable1: distribucion(parametros)
        nombre_variable2: distribucion(parametros)
        ...
        
        Args:
            ruta_archivo: Ruta al archivo de texto con el modelo
            
        Returns:
            Objeto Modelo parseado
        """
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            contenido = archivo.read()
        
        # Buscar la funcion
        patron_funcion = r'FUNCION:\s*(.+)'
        match_funcion = re.search(patron_funcion, contenido, re.IGNORECASE)
        if not match_funcion:
            raise ValueError("No se encontro la definicion FUNCION en el archivo")
        
        funcion = match_funcion.group(1).strip()
        
        # Buscar las variables
        patron_variables = r'VARIABLES:\s*\n((?:.+\n?)+)'
        match_variables = re.search(patron_variables, contenido, re.IGNORECASE | re.MULTILINE)
        if not match_variables:
            raise ValueError("No se encontraron variables en el archivo")
        
        variables_texto = match_variables.group(1).strip()
        variables = []
        
        # Parsear cada variable
        for linea in variables_texto.split('\n'):
            linea = linea.strip()
            if not linea:
                continue
            
            # Formato: nombre: distribucion(param1=valor1, param2=valor2)
            patron_var = r'(\w+):\s*(\w+)\((.*?)\)'
            match_var = re.match(patron_var, linea)
            if not match_var:
                continue
            
            nombre = match_var.group(1)
            distribucion = match_var.group(2)
            parametros_texto = match_var.group(3)
            
            # Parsear parametros
            parametros = {}
            if parametros_texto:
                for param in parametros_texto.split(','):
                    param = param.strip()
                    if '=' in param:
                        clave, valor = param.split('=')
                        parametros[clave.strip()] = float(valor.strip())
            
            variable = Variable(nombre, distribucion, parametros)
            variables.append(variable)
        
        return Modelo(funcion, variables)

