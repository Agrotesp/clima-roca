# Clima da Roça Pro

Painel em Python + Streamlit para acompanhar chuva e decisão de plantio.

## O que já vem pronto
- previsão diária e horária por coordenada
- histórico agroclimático (NASA POWER)
- status automático: AGUARDAR / ATENÇÃO / SINAL BOM
- mapa da roça
- leitura de KML e GeoJSON
- área padrão já gerada a partir do seu arquivo KML

## Arquivos principais
- `app.py` -> app principal
- `requirements.txt` -> dependências
- `areas/minha_roca.geojson` -> área padrão da roça

## Como rodar localmente
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Como publicar de graça
1. Crie uma conta no GitHub.
2. Crie um repositório novo, por exemplo: `clima-roca`.
3. Envie estes arquivos para o repositório.
4. Crie conta no Streamlit Community Cloud.
5. Conecte sua conta GitHub ao Streamlit.
6. Escolha o repositório e o arquivo `app.py`.
7. Clique em deploy.

## Sua área atual
- Arquivo de origem: `Mapa sem título.kml`
- Método usado: marcadores do KML + contorno automático
- Área aproximada: **13.49 ha**

## Pontos lidos do KML
- 1: lon -38.040307, lat -10.724774
- 2: lon -38.039394, lat -10.725191
- 3: lon -38.038820, lat -10.726413
- 4: lon -38.038933, lat -10.726744
- 5: lon -38.037210, lat -10.727476
- 6: lon -38.038454, lat -10.727072
- 7: lon -38.035986, lat -10.727783
- 8: lon -38.035687, lat -10.727810
- 9: lon -38.034687, lat -10.724906
- 10: lon -38.038346, lat -10.724799
