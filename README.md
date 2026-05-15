# InteligenciaArtificial

Un proyecto de inteligencias artificial con arquitectura full-stack:
- **Backend**: Python (FastAPI)
- **Componentes de IA**: Python
- **Frontend**: Next.js
- **Herramientas**: uv (Python), bun (JavaScript/TypeScript)
- **Despliegue**: Docker y Kubernetes

## Tabla de Contenidos
- [Características](#características)
- [Requisitos Previos](#requisitos-previos)
- [Configuración Local](#configuración-local)
- [Despliegue con Docker](#despliegue-con-docker)
- [Despliegue con Kubernetes](#despliegue-con-kubernetes)
- [Tecnologías Utilizadas](#tecnologías-utilizadas)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

## Características
- Backend en Python con FastAPI para lógica de negocio y APIs REST
- Componentes de IA especializados (machine learning, procesamiento de lenguaje natural, etc.)
- Interfaz de usuario moderna y reactiva con Next.js
- Gestión de dependencias eficiente con uv (Python) y bun (JS/TS)
- Contenerización con Docker para portabilidad
- Orquestación con Kubernetes para escalabilidad y alta disponibilidad

## Requisitos Previos
- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) (para desarrollo frontend)
- [uv](https://github.com/astral-sh/uv) (instalador de paquetes Python ultra rápido)
- [bun](https://bun.sh/) (runtime y bundler de JavaScript/TypeScript)
- [Docker](https://www.python.org/downloads/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) y [minikube](https://minikube.sigs.k8s.io/docs/start/) o acceso a un clúster de Kubernetes

## Configuración Local
### Backend (Python/FastAPI)
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python main.py
# o con uvicorn: uvicorn main:app --reload
```

### Frontend (Next.js)
```bash
cd frontend
bun install
bun run dev
```

## Despliegue con Docker
### Construir imágenes
```bash
# Backend
cd backend
docker build -t inteligencia-artificial-backend .

# Frontend
cd ../frontend
docker build -t inteligencia-artificial-frontend .
```

### Ejecutar con Docker Compose (si existe)
```bash
docker-compose up
```

## Despliegue con Kubernetes
1. Aplicar los manifiestos de Kubernetes:
```bash
kubectl apply -f k8s/
```

2. Verificar los despliegues:
```bash
kubectl get pods
kubectl get services
```

3. Acceder a la aplicación:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Tecnologías Utilizadas
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Pydantic
- **IA**: TensorFlow/PyTorch, scikit-learn, transformers, langchain
- **Frontend**: Next.js 13+, React 18, TypeScript
- **Herramientas**: 
  - uv: Instalador y gestor de paquetes Python
  - bun: Runtime JavaScript/TypeScript y bundler
- **Contenerización**: Docker
- **Orquestación**: Kubernetes
- **Otros**: 
  - NGINX (como proxy inverso opcional)
  - PostgreSQL (base de datos)
  - Prometheus & Grafana (monitoreo)

## Contribuir
1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia
Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.