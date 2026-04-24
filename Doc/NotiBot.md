# NotiBot: Plataforma de Inteligencia Artificial para Noticias de Lima

## 1. Visión General
NotiBot es una plataforma web avanzada diseñada para centralizar, clasificar y personalizar el consumo de noticias en la ciudad de Lima, Perú. Utilizando agentes inteligentes y Modelos de Lenguaje de Gran Escala (LLM), la plataforma transforma la experiencia de lectura tradicional en una red social interactiva impulsada por IA.

---

## 2. Arquitectura del Sistema

### Módulo A: Agente de Recopilación y Clasificación
El "corazón" de la plataforma encargado de alimentar la base de datos con información fresca y curada.
- **Scraping Multi-fuente**: Agente automatizado diseñado para extraer contenido de:
  - El Comercio
  - La República
  - Gestión
  - RPP Noticias
- **Procesamiento con LLM**: 
  - **Clasificación**: Categorización automática (Política, Economía, Seguridad, Deporte, etc.).
  - **Análisis de Sentimiento**: Identificar el tono de la noticia.
  - **Resumen Ejecutivo**: Generar resúmenes concisos para la vista rápida.
  - **Extracción de Entidades**: Identificar personajes, lugares y organizaciones clave.

### Módulo B: Plataforma Web (Experiencia de Usuario)
Una interfaz moderna y dinámica que fomente la interacción.
- **Feed Estilo Red Social**: Visualización de noticias mediante "cards" interactivas (Scroll infinito, reacciones como "me interesa", "importante", "falso").
- **Chatbot Inteligente (RAG)**: 
  - Un asistente virtual integrado que utiliza *Retrieval-Augmented Generation* (RAG) para responder preguntas basadas **únicamente** en las noticias almacenadas en la base de datos.
  - Capacidad para debatir puntos de vista, explicar contextos complejos y resumir hilos de noticias.

### Módulo C: Personalización y Recomendaciones (Machine Learning)
Motor de inteligencia para retener al usuario y ofrecer contenido relevante.
- **Perfil de Usuario**: Seguimiento de historial de lecturas, búsquedas realizadas y reacciones.
- **Sistema de Recomendación**: 
  - **Filtrado Basado en Contenido**: Sugerir noticias similares a las que el usuario ha reaccionado positivamente.
  - **Filtrado Colaborativo**: Recomendar noticias populares entre usuarios con gustos similares.
  - **Modelos**: Uso de Embeddings para encontrar similitudes semánticas entre el interés del usuario y el contenido disponible.

---

## 3. Stack Tecnológico Propuesto

| Componente | Tecnología Sugerida |
| :--- | :--- |
| **Backend** | Python Django |
| **Frontend** | React / Next.js |
| **Base de Datos** | PostgreSQL (Relacional) + Pinecone/ChromaDB (Vectorial para RAG) |
| **IA / LLM** | OpenAI (GPT-4o) / Anthropic (Claude 3.5) / LangChain para Agentic Workflow |
| **Scraping** | Scrapy / Playwright (para manejar JS dinámico) |
| **Machine Learning** | Scikit-learn / PyTorch para el motor de recomendaciones |

---

## 4. Fases de Implementación

1. **Fase 1: Extracción y Almacenamiento**: Configuración de los scrapers y la base de datos inicial con clasificación por LLM.
2. **Fase 2: Interfaz de Usuario Social**: Desarrollo del feed de noticias y sistema de autenticación de usuarios.
3. **Fase 3: Inteligencia Conversacional**: Implementación del chatbot con acceso a la base de datos vectorial.
4. **Fase 4: Motor de Recomendación**: Desarrollo y entrenamiento del modelo de ML basado en la actividad del usuario.
5. **Fase 5: Optimización y Lanzamiento**: Pruebas de carga, ajuste de prompts del LLM y despliegue.

---

## 5. Próximos Pasos
- [ ] Definir la estructura exacta de la base de datos.
- [ ] Crear el primer prototipo de scraper para *El Comercio*.
- [ ] Diseñar el mockup de la interfaz social.
