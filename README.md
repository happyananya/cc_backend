# AI Photo Search — Backend

Backend for Cloud Computing Assignment 3. Frontend lives in
[cloud_assingment_frontend](https://github.com/happyananya/cloud_assingment_frontend).

| Path | What |
|---|---|
| `lambda_index/` | LF1 `index-photos` — S3 PUT → Rekognition + custom labels → OpenSearch |
| `lambda_search/` | LF2 `search-photos` — `GET /search?q=` → Lex → OpenSearch |
| `buildspec.yml` | CodeBuild spec for pipeline P1 (updates both Lambdas) |
| `cloudformation/template.yaml` | T1 — buckets, Lambdas, API Gateway, API key |

## Lambda environment variables

| Var | Used by | Example |
|---|---|---|
| `ES_ENDPOINT` | both | `https://search-photos-xxxx.us-east-1.es.amazonaws.com` |
| `ES_USER`, `ES_PASS` | both | OpenSearch fine-grained access master user |
| `BOT_ID`, `BOT_ALIAS_ID` | LF2 | Lex V2 bot / alias IDs |

## Deploy the stack

```bash
aws cloudformation deploy \
  --template-file cloudformation/template.yaml \
  --stack-name photo-search \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    FrontendBucketName=<b1-name> PhotosBucketName=<b2-name> \
    EsEndpoint=https://<domain-endpoint> EsUser=<user> EsPassword=<pass> \
    BotId=<bot-id> BotAliasId=<alias-id>

aws cloudformation describe-stacks --stack-name photo-search --query "Stacks[0].Outputs"
```
