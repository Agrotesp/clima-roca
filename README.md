# Clima da Roça Pro + Telegram

Esta versão do painel já está preparada para enviar mensagens para o Telegram.

## Seu chat_id
Use este chat_id para receber no privado:

```text
1123038530
```

Se quiser enviar para o grupo depois, o ID que apareceu foi:

```text
-5195152538
```

## Importante sobre o token
Como o token do bot foi compartilhado na conversa, o ideal é:

1. Abrir o BotFather
2. Revogar o token antigo
3. Gerar um token novo
4. Usar só o token novo no app

## Arquivos do projeto
Suba estes arquivos para o GitHub:

```text
app/app.py
areas/minha_roca.geojson
requirements.txt
README.md
.streamlit/secrets.toml.example
```

## Passo a passo para finalizar e fazer chegar no Telegram

### 1) Gere um novo token no BotFather
No BotFather:

```text
/revoke
```
Escolha o bot antigo.

Depois:

```text
/token
```
Escolha o bot e copie o token novo.

### 2) Confirme que você iniciou o bot
No Telegram:
- abra o bot `Clima bot`
- clique em **Start** ou envie:

```text
/start
```

### 3) Atualize o GitHub
No seu repositório, substitua:
- `app/app.py`
- `areas/minha_roca.geojson`
- `requirements.txt`
- `README.md`
- `.streamlit/secrets.toml.example`

Depois faça o **commit**.

### 4) Configure as Secrets no Streamlit
No painel do Streamlit do seu app:
- abra o app
- clique em **Settings**
- clique em **Secrets**

Cole exatamente assim:

```toml
TELEGRAM_BOT_TOKEN = "COLE_AQUI_O_TOKEN_NOVO"
TELEGRAM_CHAT_ID = "1123038530"
```

Se depois quiser enviar para o grupo, troque o `TELEGRAM_CHAT_ID` por:

```toml
TELEGRAM_CHAT_ID = "-5195152538"
```

### 5) Reinicie o app
Depois de salvar as Secrets:
- volte para o app
- clique em **Reboot app**

### 6) Teste dentro do app
No app vai aparecer a área de Telegram. Faça nesta ordem:

1. Clique em **Buscar chats do bot**
2. Verifique se aparece seu chat privado `1123038530`
3. Clique em **Enviar teste curto**

Se chegar a mensagem, está funcionando.

### 7) Envie as mensagens automáticas do painel
Depois do teste, você já pode usar:
- **Enviar mensagem da manhã**
- **Enviar mensagem da tarde**

## Como será a mensagem

### Mensagem da manhã
```text
📡 RELATÓRIO CLIMA – MANHÃ

📍 Sua roça – Paripiranga/BA

🌧️ Situação:
Instabilidade fraca

📊 Previsão:
Hoje: 2 mm (⚠️ 40%)
Amanhã: 6 mm (⚠️ 55%)
+2 dias: 12 mm (🟡 65%)

📈 Tendência:
MELHORANDO

📡 Radar:
0 mm próximo da área

🌱 Recomendação:
🔴 AGUARDAR

💬 Ainda não é chuva firme
```

### Mensagem da tarde
```text
📡 ALERTA – TARDE

📡 Radar:
Chuva a 25 km da área

🌧️ Intensidade:
Fraca a moderada (~3 mm estimado)

📊 Acumulado esperado:
Hoje: 4 mm total (se confirmar)

⏱️ Chegada:
1–2 horas (estimado)

🌱 Recomendação:
🟡 ATENÇÃO

💬 Pode molhar superficialmente
```

## Se não chegar no Telegram
Confira nesta ordem:

1. Você clicou em `/start` no bot?
2. O token novo foi colado certo nas Secrets?
3. O `TELEGRAM_CHAT_ID` está como `1123038530`?
4. Você clicou em **Reboot app** depois de salvar?
5. O app mostrou sucesso no envio?

## Resumo final
Você vai precisar só de 2 coisas:
- token novo do bot
- seu chat_id: `1123038530`

Com isso, o app consegue enviar no Telegram.
