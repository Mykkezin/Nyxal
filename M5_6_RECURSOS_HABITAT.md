# M5.6 — Ferramentas e módulos como recursos do habitat

## Objetivo

Transformar a disponibilidade de ferramentas e módulos em recursos observáveis do habitat NyxOS.

O M5.6 não cria uma nova camada de execução. Ele descreve o que o habitat já disponibiliza:

```
capacidades declaradas + módulos existentes
              ↓
      RecursosHabitatNixOS
              ↓
        estado do habitat
              ↓
          interface
```

## Recursos

### Ferramentas

As ferramentas são derivadas de `capacidades_nixal.json` e expõem apenas metadados:

- nome;
- descrição;
- objetivo;
- argumentos declarados;
- domínios;
- estado observável.

### Módulos

Os módulos Python `nixal_*.py` são catalogados por nome e arquivo, sem importação dinâmica.

## Invariantes

- somente leitura;
- nenhuma ferramenta é executada pelo catálogo;
- nenhum módulo é importado dinamicamente;
- nenhuma dependência nova;
- nenhuma autorização de execução;
- nenhuma alteração de arquitetura;
- N9/N10 permanecem intactos.

## Critério de conclusão

M5.6 é implementado quando o habitat expõe o catálogo de recursos reais e a interface consegue apresentar sua disponibilidade sem transformar observação em execução.
