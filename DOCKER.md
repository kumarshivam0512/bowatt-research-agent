# Docker Setup

This repo can run as two containers:

- `research-backend`: FastAPI research API on port `8787`
- `research-frontend`: nginx static frontend on port `5173`, proxying `/api` to the backend

## Local Compose

Create the backend env file:

```sh
cp backend/.env.example backend/.env
```

Fill in:

```txt
OPENAI_API_KEY=
TAVILY_API_KEY=
```

Then run:

```sh
npm --prefix frontend install
npm --prefix frontend run build
docker compose up --build
```

Open:

```txt
http://localhost:5173
```

The frontend calls `/api`, and nginx forwards those requests to `research-backend:8787`.

## Kubernetes

Build images:

```sh
npm --prefix frontend install
npm --prefix frontend run build
docker build -t research-agent-backend:local ./backend
docker build -t research-agent-frontend:local -f k8s/frontend.Dockerfile ./frontend
```

Create the runtime secret:

```sh
kubectl create secret generic research-agent-env \
  --from-literal=OPENAI_API_KEY=your_openai_key \
  --from-literal=TAVILY_API_KEY=your_tavily_key \
  --from-literal=LLM_MODEL=openai:gpt-5.1 \
  --from-literal=OPENAI_REASONING_EFFORT=medium \
  --from-literal=EMBEDDING_MODEL=openai:text-embedding-3-small
```

Apply the manifests:

```sh
kubectl apply -f k8s/research-agent.yaml
```
