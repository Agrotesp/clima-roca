# Clima da Roça Pro

Painel em Python + Streamlit para acompanhar previsão, radar, histórico recente e semáforo de plantio da sua área.

## Recursos
- mapa da roça sobre satélite
- radar RainViewer sobre o mapa
- leitura automática: está chegando ou não
- semáforo de plantio
- gráficos de previsão diária e próximas 72 horas
- histórico recente NASA POWER
- upload de KML ou GeoJSON

## Estrutura
```text
app/
  app.py
areas/
  minha_roca.geojson
requirements.txt
README.md
```

## Rodar localmente
```bash
pip install -r requirements.txt
streamlit run app/app.py
```

## Publicar no Streamlit Community Cloud
1. Suba os arquivos para um repositório GitHub.
2. No Streamlit, crie um novo app.
3. Escolha o repositório.
4. Defina o arquivo principal como `app/app.py`.
5. Faça o deploy.
