# Sistema de Simulacion Montecarlo Distribuida

Este proyecto implementa un sistema distribuido para realizar simulaciones Montecarlo utilizando el modelo de paso de mensajes con RabbitMQ.

## Descripcion del Sistema

El sistema esta compuesto por tres componentes principales:

1. **Productor**: Genera escenarios unicos a partir de un modelo matematico y los publica en RabbitMQ
2. **Consumidores**: Procesan escenarios, ejecutan el modelo y publican resultados
3. **Dashboard**: Visualiza el progreso de la simulacion en tiempo real

## Requisitos

- Python 3.8 o superior
- RabbitMQ (se ejecuta desde Docker Desktop)
- Las dependencias listadas en `requirements.txt`

## Instalacion

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

2. Asegurarse de que RabbitMQ este ejecutandose en Docker Desktop

3. Verificar que RabbitMQ este accesible en `localhost:5672`

## Estructura del Proyecto

```
PF_PDYA/
├── config.py              # Configuracion del sistema
├── model_parser.py        # Parser de modelos desde archivos de texto
├── message_handler.py     # Manejo de mensajes con RabbitMQ
├── producer.py            # Productor de escenarios
├── consumer.py            # Consumidor de escenarios
├── dashboard.py           # Dashboard visualizador
├── ejemplo_modelo.txt     # Ejemplo de archivo de modelo
├── requirements.txt       # Dependencias del proyecto
└── README.md             # Este archivo
```

## Formato del Archivo de Modelo

El archivo de modelo debe tener el siguiente formato:

```
FUNCION: expresion_matematica
VARIABLES:
nombre_variable1: distribucion(parametro1=valor1, parametro2=valor2)
nombre_variable2: distribucion(parametro1=valor1)
...
```

### Distribuciones Soportadas

- **normal**: Distribucion normal
  - Parametros: `media`, `desviacion`
  - Ejemplo: `x: normal(media=10, desviacion=2)`

- **uniform**: Distribucion uniforme
  - Parametros: `min`, `max`
  - Ejemplo: `y: uniform(min=5, max=15)`

- **exponential**: Distribucion exponencial
  - Parametros: `lambda`
  - Ejemplo: `z: exponential(lambda=0.5)`

- **triangular**: Distribucion triangular
  - Parametros: `left`, `mode`, `right`
  - Ejemplo: `w: triangular(left=0, mode=5, right=10)`

### Funciones Matematicas Disponibles

En la expresion FUNCION puedes usar:
- Operaciones basicas: `+`, `-`, `*`, `/`, `**`
- Funciones de NumPy: `np.sin()`, `np.cos()`, `np.exp()`, `np.log()`, `np.sqrt()`, `np.abs()`
- Funciones de comparacion: `np.maximum()`, `np.minimum()`

## Uso del Sistema

### 1. Ejecutar el Productor

El productor lee un modelo desde un archivo de texto y genera escenarios:

```bash
python producer.py <ruta_modelo> [num_escenarios]
```

Ejemplo:
```bash
python producer.py ejemplo_modelo.txt 1000
```

Esto generara 1000 escenarios y los publicara en la cola de escenarios.

### 2. Ejecutar Consumidores

Los consumidores se pueden ejecutar en diferentes equipos. Cada consumidor necesita un ID unico:

```bash
python consumer.py <consumer_id>
```

Ejemplo (en diferentes terminales o equipos):
```bash
python consumer.py consumer_1
python consumer.py consumer_2
python consumer.py consumer_3
```

Cada consumidor:
1. Lee el modelo de la cola de modelo (una vez)
2. Obtiene escenarios de la cola de escenarios
3. Ejecuta el modelo con cada escenario
4. Publica resultados en la cola de resultados

### 3. Ejecutar el Dashboard

El dashboard muestra el progreso de la simulacion en tiempo real:

```bash
python dashboard.py
```

El dashboard muestra:
- Estadisticas generales (total de resultados, media, desviacion, etc.)
- Estadisticas por consumidor
- Grafico de resultados en tiempo real
- Histograma de la distribucion de resultados

## Flujo del Sistema

1. **Productor**:
   - Lee el modelo desde un archivo
   - Publica el modelo en la cola de modelo (con TTL)
   - Genera escenarios unicos
   - Publica cada escenario en la cola de escenarios

2. **Consumidores**:
   - Leen el modelo de la cola de modelo (una sola vez al inicio)
   - Consumen escenarios de la cola de escenarios
   - Ejecutan el modelo con los valores del escenario
   - Publican resultados en la cola de resultados

3. **Dashboard**:
   - Consume resultados de la cola de resultados
   - Actualiza las visualizaciones en tiempo real
   - Muestra estadisticas del productor y consumidores

## Configuracion

La configuracion se encuentra en `config.py`. Puedes modificar:

- `RABBITMQ_HOST`: Direccion del servidor RabbitMQ
- `RABBITMQ_PORT`: Puerto de RabbitMQ
- `RABBITMQ_USER` y `RABBITMQ_PASSWORD`: Credenciales
- `MODEL_TIMEOUT`: Tiempo de expiracion del modelo en segundos
- `NUM_ESCENARIOS_DEFAULT`: Numero de escenarios por defecto

## Colas de RabbitMQ

El sistema utiliza tres colas:

1. **cola_modelo**: Contiene el modelo a ejecutar (con TTL)
2. **cola_escenarios**: Contiene los escenarios a procesar
3. **cola_resultados**: Contiene los resultados de la simulacion

## Notas Importantes

- El modelo se publica con un TTL (time to live). Cuando se carga un nuevo modelo, el anterior expira automaticamente
- Los consumidores deben estar ejecutandose antes o despues del productor, pero necesitan el modelo para funcionar
- El dashboard puede ejecutarse en cualquier momento para ver los resultados
- Todos los componentes pueden ejecutarse en diferentes equipos, solo necesitan acceso a RabbitMQ

## Ejemplo Completo

1. Iniciar RabbitMQ en Docker Desktop

2. Ejecutar el productor:
```bash
python producer.py ejemplo_modelo.txt 500
```

3. Ejecutar uno o mas consumidores (en diferentes terminales o equipos):
```bash
python consumer.py worker_1
python consumer.py worker_2
```

4. Ejecutar el dashboard:
```bash
python dashboard.py
```

## Solucion de Problemas

- **Error de conexion a RabbitMQ**: Verificar que RabbitMQ este ejecutandose en Docker Desktop
- **Modelo no encontrado**: Verificar la ruta del archivo de modelo
- **Error al parsear modelo**: Verificar el formato del archivo de modelo
- **Dashboard no muestra datos**: Verificar que haya consumidores procesando escenarios

## Arquitectura

El sistema sigue el paradigma orientado a objetos con las siguientes clases principales:

- `Variable`: Representa una variable con su distribucion
- `Modelo`: Representa un modelo matematico completo
- `ParserModelo`: Parsea archivos de texto a objetos Modelo
- `ManejadorMensajes`: Clase base para comunicacion con RabbitMQ
- `Publicador`: Publica mensajes en las colas
- `Consumidor`: Consume mensajes de las colas
- `Productor`: Genera y publica escenarios
- `ConsumidorEscenarios`: Procesa escenarios y genera resultados
- `Dashboard`: Interfaz grafica para visualizacion

## Autor

Sistema desarrollado como proyecto academico para simulacion Montecarlo distribuida.

