#!/usr/bin/env bash
# Start a ROCm/vLLM OpenAI-compatible endpoint on AMD Developer Cloud.
# Bind to loopback only: connect from NyxOS through an SSH local-forward.
set -euo pipefail

IMAGE="${NYXAL_AMD_VLLM_IMAGE:-vllm/vllm-openai-rocm:latest}"
MODEL="${NYXAL_AMD_CLOUD_MODEL:-Qwen/Qwen3.5-35B-A3B}"
PORT="${NYXAL_AMD_CLOUD_PORT:-8001}"
MAX_MODEL_LEN="${NYXAL_AMD_MAX_MODEL_LEN:-65536}"
GPU_MEMORY_UTILIZATION="${NYXAL_AMD_GPU_MEMORY_UTILIZATION:-0.90}"
CONTAINER="${NYXAL_AMD_VLLM_CONTAINER:-nyxal-vllm-rocm}"
TENSOR_PARALLEL_SIZE="${NYXAL_AMD_TENSOR_PARALLEL_SIZE:-1}"

fail() {
  printf 'ERRO: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker não está instalado."
docker info >/dev/null 2>&1 || fail "Docker não está acessível; verifique o serviço/permissões."

[[ -c /dev/kfd ]] || fail "/dev/kfd ausente. Confirme que esta instância expõe uma GPU AMD compatível."
[[ -d /dev/dri ]] || fail "/dev/dri ausente. Confirme a imagem ROCm e os dispositivos da GPU."
[[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1024 && PORT <= 65535 )) || fail "NYXAL_AMD_CLOUD_PORT deve estar entre 1024 e 65535."
[[ "$MAX_MODEL_LEN" =~ ^[0-9]+$ ]] && (( MAX_MODEL_LEN >= 1024 && MAX_MODEL_LEN <= 262144 )) || fail "NYXAL_AMD_MAX_MODEL_LEN inválido."
[[ "$TENSOR_PARALLEL_SIZE" =~ ^[1-8]$ ]] || fail "NYXAL_AMD_TENSOR_PARALLEL_SIZE deve estar entre 1 e 8."
[[ "$MODEL" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]] || fail "Nome do modelo contém caracteres não permitidos."
[[ "$GPU_MEMORY_UTILIZATION" =~ ^0\.[0-9]+$ ]] || fail "NYXAL_AMD_GPU_MEMORY_UTILIZATION deve ser um decimal entre 0 e 1."
awk -v value="$GPU_MEMORY_UTILIZATION" 'BEGIN { exit !(value > 0 && value < 1) }' || fail "GPU memory utilization deve ser maior que 0 e menor que 1."

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  fail "O container '$CONTAINER' já existe. Inspecione-o antes de removê-lo; este script não substitui containers automaticamente."
fi

printf 'Imagem: %s\nModelo: %s\nPorta loopback: %s\n' "$IMAGE" "$MODEL" "$PORT"
printf 'O endpoint escutará em 127.0.0.1; use um túnel SSH e não abra a porta publicamente.\n'

mkdir -p "$HOME/.cache/huggingface"
docker pull "$IMAGE"

docker run --detach \
  --name "$CONTAINER" \
  --restart unless-stopped \
  --network host \
  --ipc host \
  --device=/dev/kfd \
  --device=/dev/dri \
  --security-opt seccomp=unconfined \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
  --entrypoint python3 \
  "$IMAGE" \
  -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --trust-remote-code \
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
  --max-model-len "$MAX_MODEL_LEN" \
  --tensor-parallel-size "$TENSOR_PARALLEL_SIZE" \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  --reasoning-parser qwen3

printf '\nContainer iniciado: %s\n' "$CONTAINER"
printf 'Acompanhe o carregamento do modelo com:\n  docker logs -f %s\n' "$CONTAINER"
printf 'O servidor estará pronto quando os logs indicarem que a aplicação iniciou.\n'
printf 'Endpoint local na VM:\n  curl http://127.0.0.1:%s/v1/models\n' "$PORT"
printf '\nPara usar no NyxOS, mantenha um túnel ativo:\n'
printf '  ssh -N -L %s:127.0.0.1:%s root@<IP_DA_VM>\n' "$PORT" "$PORT"
printf 'E configure NYXAL_AMD_CLOUD_BASE_URL=http://127.0.0.1:%s/v1\n' "$PORT"
