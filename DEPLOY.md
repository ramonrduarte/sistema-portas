# Deploy — Sistema de Portas (rdmon.com)

Guia para subir o sistema no servidor caseiro via Portainer, usando Traefik como proxy reverso.

## Pré-requisitos no servidor

- Docker + Portainer instalados
- Traefik rodando com a rede `network_public` externa criada
- DNS `portas.rdmon.com` apontando para o IP do servidor

## 1. Criar a stack no Portainer

1. Abra o Portainer → **Stacks** → **Add stack**
2. Nome da stack: `portas`
3. Selecione **Repository**:
   - URL: `https://github.com/ramonrduarte/sistema-portas.git`
   - Branch: `feature/api-assistente-gpt` (ou `main` para produção estável)
   - Compose path: `docker-compose.rdmon.yml`
4. Ative **Automatic updates** se quiser redeploy automático a cada push

## 2. Configurar as variáveis de ambiente

Na seção **Environment variables** do Portainer, adicione:

```
SECRET_KEY=<chave-longa-e-aleatória>
DATABASE_PASSWORD=<senha-forte>
GPT_API_TOKEN=<chave-openai>
```

As demais variáveis já têm valores padrão no `docker-compose.rdmon.yml`:

| Variável | Padrão |
|---|---|
| `ALLOWED_HOSTS` | `portas.rdmon.com,localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | `https://portas.rdmon.com` |
| `DATABASE_NAME` | `portas_rdmon` |
| `DATABASE_USER` | `postgres` |
| `SESSION_COOKIE_SECURE` | `False` |
| `CSRF_COOKIE_SECURE` | `False` |

> **Nota:** `SESSION_COOKIE_SECURE` e `CSRF_COOKIE_SECURE` estão `False` intencionalmente para ambiente de testes. Para produção real, use `docker-compose.yml` (servidor da empresa) com os valores `True`.

## 3. Fazer o deploy

Clique em **Deploy the stack**. Na primeira execução, o build leva alguns minutos.

O container `portas` aguarda o postgres estar saudável antes de iniciar (via healthcheck), então `migrate` e `collectstatic` rodam automaticamente sem erro de conexão.

## 4. Verificar

- Acesse `https://portas.rdmon.com`
- Ou internamente: `http://<ip-servidor>:<porta>` (se expor a porta diretamente)
- No Portainer, acompanhe os logs do container `portas` para ver as migrations

## 5. Atualizar após um push

No Portainer → **Stacks** → `portas` → **Pull and redeploy**

---

## Acesso ao banco de dados

O postgres roda em container isolado na rede `internal`, inacessível externamente. Para acessar:

```bash
docker exec -it <container-postgres> psql -U postgres -d portas_rdmon
```

## Diferenças em relação ao servidor da empresa

| | Empresa (`docker-compose.yml`) | Casa (`docker-compose.rdmon.yml`) |
|---|---|---|
| Domínio | `portas.adrofecha.com.br` | `portas.rdmon.com` |
| Postgres | Externo (já existe no servidor) | Incluso na stack |
| HTTPS seguro | Sim (`SECURE=True`) | Não (testes) |
| Branch | `main` | `feature/api-assistente-gpt` |
