import pandas as pd
import requests
from flask import Flask, request, jsonify

# Configurações
DEEPSEEK_API_KEY = 'sk-e6be20b8803147fa9e7dfccedbfed170'
ULTRAMSG_INSTANCE_ID = 'instance133000'  # Substitua pelo seu Instance ID
ULTRAMSG_TOKEN = '8vdony9tlrimcce0'              # Substitua pelo seu Token
CSV_PATH = 'contatos.csv'

# Dados fixos para respostas rápidas
INFO = {
    "local": "Laboratório de Robótica do SEDECTI, Rua Campinas 26 Térreo, Santa Teresa.",
    "horario": "Turma 1 das 8h00 às 11h00 e Turma 2 das 18h00 às 21h00.",
    "vagas": "Sim.",
    "inscricao": "bit.ly/citha"
}

def resposta_rapida(pergunta):
    p = pergunta.lower()
    if ("local" in p or ("onde" in p and "aula" in p)):
        return f"O local das aulas é: {INFO['local']}"
    if "horário" in p or "hora" in p:
        return f"Horário das aulas: {INFO['horario']}"
    if "vaga" in p:
        return f"Ainda tem vagas? {INFO['vagas']}"
    if "inscrev" in p or "matricul" in p:
        return f"Para se inscrever, acesse: {INFO['inscricao']}"
    return None

def responder_ia(pergunta):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Você é um assistente educacional. Use as informações: Local das aulas: Laboratório de Robótica do SEDECTI, Rua Campinas 26 Térreo, Santa Teresa. Horário das Aulas: Turma 1 das 8h00 às 11h00 e Turma 2 das 18h00 às 21h00. Ainda tem vagas: Sim. Onde me inscrevo: bit.ly/citha"},
            {"role": "user", "content": pergunta}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        resposta = response.json()
        return resposta['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Erro ao gerar resposta: {e}"

def enviar_whatsapp(telefone, mensagem):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE_ID}/messages/chat"
    data = {
        "token": ULTRAMSG_TOKEN,
        "to": telefone,
        "body": mensagem
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        print(f"Mensagem enviada para {telefone}")
    except Exception as e:
        print(f"Erro ao enviar mensagem para {telefone}: {e}")

def registrar_pergunta_resposta(telefone, pergunta, resposta):
    df = pd.read_csv(CSV_PATH)
    telefone = str(telefone).strip()
    idx = df[df['Telefone'].astype(str).str.strip() == telefone].index
    if not idx.empty:
        df.at[idx[0], 'Pergunta'] = pergunta
        df.at[idx[0], 'Resposta'] = resposta
        df.to_csv(CSV_PATH, index=False)
        return True
    return False

# Flask app para webhook
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    if not request.is_json:
        return jsonify({"status": "erro", "mensagem": "Requisição não é JSON."}), 400
    data = request.get_json()
    telefone = str(data.get('from', '')).strip()
    pergunta = data.get('body', '').strip()
    if not telefone or not pergunta:
        return jsonify({"status": "erro", "mensagem": "Dados insuficientes."}), 400
    # Verifica se o telefone está cadastrado
    df = pd.read_csv(CSV_PATH)
    if telefone not in df['Telefone'].astype(str).str.strip().values:
        return jsonify({"status": "ignorado", "mensagem": "Telefone não cadastrado."}), 403
    # Gera resposta
    resposta = resposta_rapida(pergunta)
    if not resposta:
        resposta = responder_ia(pergunta)
    # Envia resposta pelo WhatsApp
    enviar_whatsapp(telefone, resposta)
    # Registra pergunta e resposta no CSV
    registrar_pergunta_resposta(telefone, pergunta, resposta)
    return jsonify({"status": "ok", "resposta": resposta})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
