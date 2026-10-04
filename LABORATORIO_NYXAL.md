# NYXAL — LABORATÓRIO REMOTO

## Objetivo

Criar um ambiente experimental remoto para que a Nyxal possa testar uma hipótese sem executar o artefato diretamente no computador principal.

Fluxo:

hipótese
  ↓
artefato experimental
  ↓
branch experimento/*
  ↓
workflow_dispatch
  ↓
GitHub-hosted runner
  ↓
cópia somente de experimento/
  ↓
execução controlada
  ↓
result.json + logs
  ↓
Nyxal consulta o resultado
  ↓
comparação com baseline

## Decisão arquitetural

O workflow do laboratório deve ser um componente confiável e ficar na branch estável.

A branch experimental é tratada como dado não confiável. O workflow recebe a referência experimental como entrada, mas a definição do laboratório não é lida da branch experimental.

Para a primeira implementação, o acionamento é por workflow_dispatch. O workflow é executado a partir da branch padrão e faz checkout da ref experimental informada.

Isso separa a lógica confiável do laboratório do código que está sendo testado.

## Contrato do experimento

Cada experimento possui:

experimento/
  manifesto.json
  <arquivos do experimento>

Manifesto mínimo:

{
  "versao": 1,
  "experimento_id": "exemplo-001",
  "entrypoint": "experimento/main.py",
  "timeout_seconds": 60,
  "descricao": "Experimento controlado"
}

Campos permitidos:

- versao: deve ser 1;
- experimento_id: deve corresponder ao dispatch;
- entrypoint: somente Python dentro de experimento/;
- timeout_seconds: entre 1 e 120;
- descricao: texto opcional.

Nenhum comando de shell é recebido pelo manifesto.

## Isolamento da execução

O laboratório:

- usa runner hospedado pelo GitHub;
- concede somente contents: read;
- usa persist-credentials: false;
- não expõe GITHUB_TOKEN ao processo experimental;
- copia apenas experimento/ para diretório temporário;
- executa Python em modo isolado (-I);
- limita CPU, memória virtual e tamanho máximo de arquivo;
- impõe timeout;
- registra stdout/stderr;
- produz resultado estruturado;
- publica os resultados como artifact temporário.

Importante: esta primeira versão é um laboratório CI efêmero, não uma sandbox de segurança absoluta. O processo experimental ainda roda em um runner com rede disponível. Experimentos não confiáveis não devem receber secrets, credenciais, permissões de escrita ou acesso a ambientes de produção.

## Resultado

O laboratório produz um result.json com:

{
  "status": "sucesso | falha | timeout | runner_error",
  "experimento_sucesso": true,
  "exit_code": 0,
  "timeout": false,
  "tempo_execucao_ms": 123.4,
  "memoria_maxima_kb": 12345,
  "experiment_sha": "...",
  "stable_modificada": false,
  "autorizacao_explicita": false
}

A falha do experimento não é tratada como falha da infraestrutura. É evidência que o ciclo pode usar para rejeitar uma hipótese.

## Próxima integração

O módulo local previsto é:

nixal_laboratorio_remoto.py

Responsabilidades:

criar branch experimental
→ publicar somente os artefatos permitidos
→ disparar workflow confiável
→ consultar execução
→ recuperar resultado/log
→ entregar evidência para Evolução Controlada

Ele não deve:

- fazer merge em stable;
- forçar refs;
- conceder autorização de integração;
- alterar arquitetura automaticamente.

## Relação com Delta

O laboratório produz evidência para uma transição potencial:

ESTADO A
  ↓
experimento
  ↓
evidência
  ↓
avaliação
  ↓
ESTADO B candidato

Somente depois de autorização e validação adicional o sistema poderá registrar uma mudança Delta efetiva.

## Estado desta etapa

Esta etapa define a infraestrutura confiável do laboratório remoto.

A prova end-to-end desejada é:

branch → dispatch → runner → result.json → leitura local
