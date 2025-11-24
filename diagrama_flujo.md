# Diagrama de Flujo del Sistema de Simulacion Montecarlo Distribuida

## Diagrama de Flujo General

```
                    INICIO DEL SISTEMA
                           |
                           v
        +----------------------------------+
        |  1. PRODUCTOR                   |
        |  - Lee modelo desde archivo     |
        |  - Parsea modelo                |
        |  - Conecta a RabbitMQ           |
        +----------------------------------+
                           |
                           v
        +----------------------------------+
        |  2. PUBLICAR MODELO              |
        |  - Serializa modelo              |
        |  - Publica en cola_modelo        |
        |  - Configura TTL (timeout)       |
        +----------------------------------+
                           |
                           v
        +----------------------------------+
        |  3. GENERAR ESCENARIOS          |
        |  Para cada escenario:            |
        |  - Genera valores aleatorios     |
        |    segun distribuciones          |
        |  - Asigna ID unico               |
        |  - Publica en cola_escenarios    |
        +----------------------------------+
                           |
                           v
        +----------------------------------+
        |  4. CONSUMIDORES (N instancias) |
        |  Cada consumidor:                |
        |  a) Lee modelo (una vez)        |
        |     desde cola_modelo            |
        |  b) Deserializa modelo           |
        |  c) Almacena modelo en memoria   |
        +----------------------------------+
                           |
                           v
        +----------------------------------+
        |  5. PROCESAMIENTO DE ESCENARIOS  |
        |  Loop continuo:                  |
        |  - Consume escenario de cola    |
        |  - Ejecuta modelo con valores    |
        |  - Calcula resultado             |
        |  - Publica resultado en          |
        |    cola_resultados               |
        |  - Confirma procesamiento        |
        +----------------------------------+
                           |
                           v
        +----------------------------------+
        |  6. DASHBOARD                    |
        |  - Conecta a RabbitMQ            |
        |  - Consume resultados            |
        |  - Actualiza estadisticas        |
        |  - Actualiza graficos            |
        |  - Muestra en tiempo real        |
        +----------------------------------+
                           |
                           v
                      FIN DEL SISTEMA
```

## Flujo Detallado del Productor

```
INICIO PRODUCTOR
    |
    v
Cargar archivo de modelo
    |
    v
Parser parsea el archivo
    |
    v
Crear objeto Modelo
    |
    v
Conectar a RabbitMQ
    |
    v
Declarar colas (modelo, escenarios, resultados)
    |
    v
Serializar modelo
    |
    v
Publicar modelo en cola_modelo (con TTL)
    |
    v
Para i = 1 hasta num_escenarios:
    |
    v
    Generar escenario aleatorio
    (usando distribuciones de variables)
    |
    v
    Crear mensaje con ID y valores
    |
    v
    Publicar en cola_escenarios
    |
    v
    Incrementar contador
    |
    v
Fin del loop
    |
    v
Cerrar conexion
    |
    v
FIN PRODUCTOR
```

## Flujo Detallado del Consumidor

```
INICIO CONSUMIDOR
    |
    v
Conectar a RabbitMQ
    |
    v
Inicializar publicador de resultados
    |
    v
+-------------------------------+
| CARGAR MODELO (una vez)       |
|                               |
| Consumir de cola_modelo       |
|   |                           |
|   v                           |
| Recibir mensaje de modelo     |
|   |                           |
|   v                           |
| Deserializar modelo           |
|   |                           |
|   v                           |
| Almacenar modelo en memoria   |
|   |                           |
|   v                           |
| Confirmar recepcion           |
|   |                           |
|   v                           |
| Marcar modelo_cargado = True  |
+-------------------------------+
    |
    v
+-------------------------------+
| PROCESAR ESCENARIOS (loop)    |
|                               |
| Consumir de cola_escenarios   |
|   |                           |
|   v                           |
| Recibir mensaje de escenario  |
|   |                           |
|   v                           |
| Extraer ID y valores          |
|   |                           |
|   v                           |
| Ejecutar modelo con valores   |
|   |                           |
|   v                           |
| Calcular resultado            |
|   |                           |
|   v                           |
| Crear mensaje de resultado    |
|   |                           |
|   v                           |
| Publicar en cola_resultados   |
|   |                           |
|   v                           |
| Confirmar procesamiento       |
|   |                           |
|   v                           |
| Incrementar contadores        |
|   |                           |
|   v                           |
| Volver a consumir escenario   |
+-------------------------------+
    |
    v
FIN CONSUMIDOR (al recibir Ctrl+C)
```

## Flujo Detallado del Dashboard

```
INICIO DASHBOARD
    |
    v
Inicializar interfaz grafica (PyQt5)
    |
    v
Crear receptor de resultados (thread)
    |
    v
Conectar a RabbitMQ
    |
    v
Iniciar timer de actualizacion (cada 1 segundo)
    |
    v
+-------------------------------+
| CONSUMIR RESULTADOS (thread)  |
|                               |
| Loop continuo:                |
|   |                           |
|   v                           |
| Consumir de cola_resultados   |
|   |                           |
|   v                           |
| Recibir mensaje de resultado  |
|   |                           |
|   v                           |
| Parsear resultado             |
|   |                           |
|   v                           |
| Agregar a lista de resultados |
|   |                           |
|   v                           |
| Actualizar estadisticas       |
|   consumidores                |
|   |                           |
|   v                           |
| Emitir señal a UI             |
|   |                           |
|   v                           |
| Confirmar recepcion           |
+-------------------------------+
    |
    v
+-------------------------------+
| ACTUALIZAR UI (cada segundo)  |
|                               |
| Calcular estadisticas:        |
| - Total resultados            |
| - Media                       |
| - Desviacion estandar         |
| - Minimo/Maximo               |
|   |                           |
|   v                           |
| Actualizar grafico tiempo     |
| real                          |
|   |                           |
|   v                           |
| Actualizar histograma         |
|   |                           |
|   v                           |
| Actualizar tabla consumidores |
|   |                           |
|   v                           |
| Redibujar graficos            |
+-------------------------------+
    |
    v
FIN DASHBOARD (al cerrar ventana)
```

## Diagrama de Comunicacion entre Componentes

```
    PRODUCTOR                    RABBITMQ                    CONSUMIDORES
        |                            |                            |
        |--- Conectar -------------->|                            |
        |                            |                            |
        |--- Declarar colas -------->|                            |
        |                            |                            |
        |--- Publicar modelo ------->|                            |
        |                    [cola_modelo]                        |
        |                            |                            |
        |                            |<--- Consumir modelo -------|
        |                            |                            |
        |--- Publicar escenario 1 -->|                            |
        |                    [cola_escenarios]                    |
        |                            |                            |
        |--- Publicar escenario 2 -->|                            |
        |                    [cola_escenarios]                    |
        |                            |                            |
        |--- Publicar escenario N -->|                            |
        |                    [cola_escenarios]                    |
        |                            |                            |
        |                            |<--- Consumir escenario ----|
        |                            |                            |
        |                            |--- Publicar resultado ---->|
        |                    [cola_resultados]                    |
        |                            |                            |
        |                            |<--- Consumir resultado ----|
        |                            |                            |
        |                            |         DASHBOARD          |
```

## Flujo de Datos

```
ARCHIVO MODELO
    |
    v
PRODUCTOR
    |
    +---> MODELO (serializado) ---> [cola_modelo] ---> CONSUMIDORES
    |                                                      |
    |                                                      v
    |                                                  MODELO (en memoria)
    |                                                      |
    +---> ESCENARIOS ---> [cola_escenarios] ---> CONSUMIDORES
                                                      |
                                                      v
                                                  PROCESAMIENTO
                                                      |
                                                      v
                                                  RESULTADOS ---> [cola_resultados]
                                                                      |
                                                                      v
                                                                  DASHBOARD
                                                                      |
                                                                      v
                                                                  VISUALIZACION
```

## Estados del Sistema

```
ESTADO INICIAL
    - Colas vacias
    - Sin modelo cargado
    - Sin escenarios generados

ESTADO DESPUES DE PRODUCTOR
    - Modelo en cola_modelo (con TTL)
    - N escenarios en cola_escenarios
    - Cola_resultados vacia

ESTADO CON CONSUMIDORES ACTIVOS
    - Modelo cargado en cada consumidor
    - Escenarios siendo procesados
    - Resultados siendo generados
    - Resultados en cola_resultados

ESTADO CON DASHBOARD ACTIVO
    - Resultados siendo consumidos
    - Estadisticas siendo calculadas
    - Graficos siendo actualizados
    - Visualizacion en tiempo real
```

## Manejo de Errores

```
ERROR EN PRODUCTOR
    - Error al leer archivo: Mostrar mensaje y terminar
    - Error al parsear: Mostrar mensaje y terminar
    - Error de conexion: Reintentar o terminar

ERROR EN CONSUMIDOR
    - Error al cargar modelo: Reintentar consumo
    - Error al ejecutar modelo: Rechazar mensaje (no reencolar)
    - Error de conexion: Reintentar conexion

ERROR EN DASHBOARD
    - Error al recibir resultado: Rechazar mensaje
    - Error de conexion: Mostrar mensaje en UI
    - Error en graficos: Continuar sin actualizar grafico
```

## Politica de TTL (Time To Live)

```
MODELO PUBLICADO
    |
    v
Configurar TTL = MODEL_TIMEOUT segundos
    |
    v
Mensaje expira automaticamente despues de TTL
    |
    v
Si se publica nuevo modelo:
    - El anterior ya expiro (o esta por expirar)
    - Los consumidores nuevos obtienen el modelo actual
    - Los consumidores antiguos siguen con modelo en memoria
```

Este diagrama muestra el flujo completo del sistema de simulacion Montecarlo distribuida, desde la generacion de escenarios hasta la visualizacion de resultados.

