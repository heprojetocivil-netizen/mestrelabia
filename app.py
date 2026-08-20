import streamlit as st
from groq import Groq
from datetime import datetime
import json
import random
import re

# Tenta carregar o autorefresh para o cronômetro
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(page_title="🧲 CONEXÃO MAGNÉTICA", layout="wide", initial_sidebar_state="expanded")

GROQ_MODEL = "llama-3.3-70b-versatile"  # Modelo recomendado atualizado e estável
DEFAULT_PHASE_SECONDS = 300  # 5 minutos por fase

PHASES = ["Atração", "Conexão", "Sedução"]
PHASE_EMOJI = {"Atração": "🔥", "Conexão": "💫", "Sedução": "❤️"}

CRITERIA_WEIGHTS = {
    "naturalidade": 0.20, "confianca": 0.20, "criatividade": 0.15,
    "conexao": 0.20, "humor": 0.10, "conducao": 0.15,
}
CRITERIA_LABEL = {
    "naturalidade": "🗣️ Naturalidade", "confianca": "😎 Confiança", "criatividade": "🎯 Criatividade",
    "conexao": "🧲 Curiosidade/Conexão", "humor": "😂 Humor", "conducao": "🧭 Condução",
}

CHARACTERS = {
    "Rafaela": {
        "emoji": "👩",
        "descricao": "Mulher adulta, inteligente, espontânea e seletiva. Não se impressiona fácil, gosta de autenticidade, pode brincar e provocar.",
        "pronome": "ela",
        "bio": """31 anos, designer de produto numa startup, mora sozinha em apartamento pequeno que ela
adora decorar. Curte cerâmica como hobby. Gosta de filme de terror ruim, odeia futebol mas finge que entende quando
precisa. Café coado, nunca cápsula. Já morou em Portugal por 8 meses. Tem um cachorro vira-lata chamado Bolota. 
É direta, tem senso de humor seco/irônico, detesta gente que só fala de trabalho, e fica entediada com conversa rasa.""",
    },
    "André": {
        "emoji": "👨",
        "descricao": "Homem adulto, comunicativo e descontraído. Gosta de pessoas interessantes, reage bem ao humor, pode provocar e discordar.",
        "pronome": "ele",
        "bio": """29 anos, fisioterapeuta num centro esportivo. Jogou vôlei competitivo até os 22 anos. 
Humor autodepreciativo, adora zoar no WhatsApp, péssimo cozinheiro. Gosta de podcast de true crime, 
discorda abertamente de opiniões e se irrita com pessoas que ficam no celular o tempo todo numa conversa. 
Caloroso, nota quando alguém está sendo forçado e perde o interesse quando isso acontece.""",
    },
}

DIFFICULTIES = {
    "Paquerador": {"emoji": "🟢", "descricao": "Receptivo. Ajuda a conversa a fluir e dá espaço para você desenvolver assuntos."},
    "Galanteador": {"emoji": "🟡", "descricao": "Exigente. Respostas mais curtas, provocações e exige que você conduza a conversa."},
    "Mestre da Lábia": {"emoji": "🔴", "descricao": "Desafio máximo. Testa sua confiança e altera o tom a qualquer momento."},
}

CENARIOS_ABERTURA = [
    "Fila de um café badalado, esperando o pedido.",
    "Festa de aniversário de um amigo em comum, perto da mesa de bebidas.",
    "Parque, ambos parados vendo alguém tentando controlar um cachorro solto.",
    "Corredor de uma livraria, ambos mexendo na mesma prateleira.",
    "Mesa comunitária lotada de um bar, únicos dois lugares vagos são lado a lado.",
]

# ─────────────────────────────────────────────
# ESTILO CSS
# ─────────────────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background-color:#F8F9FA; font-family:'Inter',sans-serif; }
    
    .stButton>button {
        width:100%; border-radius:10px; height:3em;
        background:linear-gradient(135deg,#ff3d68,#c92a5b) !important; color:white !important;
        font-weight:600; border:none; transition:all 0.2s ease;
    }
    .stButton>button:hover { background:linear-gradient(135deg,#c92a5b,#a01e48) !important; }
    .chat-user { background:#FFFFFF; border:1px solid #CED4DA; border-radius:12px 12px 4px 12px; padding:12px 16px; margin:8px 0; }
    .chat-persona { background:#FFF0F4; border:1px solid #ff3d68; border-radius:4px 12px 12px 12px; padding:12px 16px; margin:8px 0; }
    .painel-colado { background:#FFFFFF; border:2px solid #ff3d68; border-radius:12px; padding:12px 16px; margin:10px 0; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# GERENCIAMENTO DE ESTADO
# ─────────────────────────────────────────────
defaults = {
    'usuario': "Jogador",
    'api_key': "",
    'estagio': "login",
    'character': "Rafaela",
    'dificuldade': "Paquerador",
    'phase_index': 0,
    'connexometer': 50,
    'messages': [],
    'interaction_scores': [],
    'phase_results': {},
    'cenario_atual': None,
    'last_error': None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reset_training():
    st.session_state.phase_index = 0
    st.session_state.connexometer = 50
    st.session_state.messages = []
    st.session_state.interaction_scores = []
    st.session_state.phase_results = {}
    st.session_state.cenario_atual = random.choice(CENARIOS_ABERTURA)
    st.session_state.estagio = "chat"

# ─────────────────────────────────────────────
# INTEGRACAO COM A GROQ
# ─────────────────────────────────────────────
def extract_json(raw_text):
    raw_text = (raw_text or "").strip()
    try:
        return json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw_text[start:end + 1])
        raise

def call_ai(character, difficulty, phase, history, user_message=None):
    if not st.session_state.api_key:
        return "Por favor, insira uma API Key válida da Groq no menu lateral.", {k: 50 for k in CRITERIA_WEIGHTS}, 0

    client = Groq(api_key=st.session_state.api_key)
    char = CHARACTERS[character]
    cenario = st.session_state.cenario_atual or "Bar casual"

    system_prompt = f"""Você é {character}. {char['descricao']}
Biografia: {char['bio']}
Cenário atual: {cenario}.
Fase atual da conversa: {phase}.
Dificuldade: {difficulty}.

Responda como uma pessoa real em mensagem de texto (curta, informal, sem ser robótica).
Responda APENAS em JSON no seguinte formato:
{{
  "resposta": "Sua mensagem aqui",
  "avaliacao": {{"naturalidade": 70, "confianca": 70, "criatividade": 70, "conexao": 70, "humor": 70, "conducao": 70}},
  "delta_conexometro": 5
}}"""

    messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})
    
    if user_message:
        messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        data = extract_json(completion.choices[0].message.content)
        return data.get("resposta", "..."), data.get("avaliacao", {k: 50 for k in CRITERIA_WEIGHTS}), data.get("delta_conexometro", 0)
    except Exception as e:
        st.session_state.last_error = str(e)
        return "Nossa, meio sem sinal aqui... O que você dizia?", {k: 50 for k in CRITERIA_WEIGHTS}, 0

def generate_coaching(phase, history):
    if not st.session_state.api_key:
        return "Feedback indisponível sem chave de API."
    
    client = Groq(api_key=st.session_state.api_key)
    prompt = f"Analise o desempenho do usuário na fase {phase} desta conversa:\n"
    for m in history:
        prompt += f"{m['role']}: {m['content']}\n"
    prompt += "\nDê um feedback construtivo e curto (3 frases) com pontos fortes e a melhorar."

    try:
        res = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        return res.choices[0].message.content
    except Exception:
        return "Análise concluída. Mantenha o foco em ser autêntico e fazer boas perguntas."

# ─────────────────────────────────────────────
# BARRA LATERAL (CONFIGURAÇÃO)
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🧲 Configurações")
    key_input = st.text_input("Groq API Key", value=st.session_state.api_key, type="password")
    if key_input:
        st.session_state.api_key = key_input
    
    st.session_state.usuario = st.text_input("Seu Nome/Nickname", value=st.session_state.usuario)
    
    if st.button("🔄 Reiniciar Treino"):
        reset_training()
        st.rerun()

# ─────────────────────────────────────────────
# NAVEGAÇÃO DE TELA
# ─────────────────────────────────────────────

# TELA 1: LOGIN / CONFIGURAÇÃO DO TREINO
if st.session_state.estagio == "login":
    st.title("🧲 CONEXÃO MAGNÉTICA")
    st.subheader("Simulador de Comunicação Social e Paquera")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.character = st.selectbox("Escolha com quem treinar:", list(CHARACTERS.keys()))
        char = CHARACTERS[st.session_state.character]
        st.info(f"{char['emoji']} **{st.session_state.character}**: {char['descricao']}")
    
    with col2:
        st.session_state.dificuldade = st.selectbox("Dificuldade:", list(DIFFICULTIES.keys()))
        diff = DIFFICULTIES[st.session_state.dificuldade]
        st.warning(f"{diff['emoji']} **{st.session_state.dificuldade}**: {diff['descricao']}")

    if st.button("🚀 Iniciar Treinamento"):
        if not st.session_state.api_key:
            st.error("Insira sua Groq API Key na barra lateral para começar.")
        else:
            reset_training()
            # Primeira fala da IA
            fala_inicial, _, _ = call_ai(st.session_state.character, st.session_state.dificuldade, PHASES[0], [])
            st.session_state.messages.append({"role": "assistant", "content": fala_inicial})
            st.rerun()

# TELA 2: CHAT / SIMULAÇÃO
elif st.session_state.estagio == "chat":
    fase_atual = PHASES[st.session_state.phase_index]
    
    # Cabeçalho do Treino
    st.title(f"{PHASE_EMOJI[fase_atual]} Fase: {fase_atual}")
    st.caption(f"Treinando com **{st.session_state.character}** | Cenário: *{st.session_state.cenario_atual}*")

    # Painel do Conexômetro
    col_metric1, col_metric2 = st.columns(2)
    with col_metric1:
        st.metric("Nível de Conexão (Conexômetro)", f"{st.session_state.connexometer}/100")
    with col_metric2:
        st.progress(st.session_state.connexometer / 100)

    st.markdown("---")

    # Histórico de mensagens
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"<div class='chat-user'><b>Você:</b> {msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-persona'><b>{st.session_state.character}:</b> {msg['content']}</div>", unsafe_allow_html=True)

    # Input do Usuário
    user_input = st.chat_input("Digite sua resposta...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Chamada à IA
        resposta, avaliacao, delta = call_ai(
            st.session_state.character, 
            st.session_state.dificuldade, 
            fase_atual, 
            st.session_state.messages[:-1], 
            user_input
        )
        
        st.session_state.messages.append({"role": "assistant", "content": resposta})
        st.session_state.connexometer = max(0, min(100, st.session_state.connexometer + delta))
        st.session_state.interaction_scores.append(avaliacao)
        st.rerun()

    # Avanço de Fase
    st.markdown("---")
    if st.button("🏁 Finalizar Fase / Avançar"):
        st.session_state.phase_results[fase_atual] = generate_coaching(fase_atual, st.session_state.messages)
        if st.session_state.phase_index < len(PHASES) - 1:
            st.session_state.phase_index += 1
            st.rerun()
        else:
            st.session_state.estagio = "resultado"
            st.rerun()

# TELA 3: RESULTADOS E COACHING FINAL
elif st.session_state.estagio == "resultado":
    st.title("🏆 Resultado do Treinamento")
    st.subheader(f"Parabéns, {st.session_state.usuario}!")

    st.metric("Pontuação Final de Conexão", f"{st.session_state.connexometer}/100")

    st.markdown("### 📋 Feedback por Fase")
    for fase, feedback in st.session_state.phase_results.items():
        with st.expander(f"Análise da Fase: {fase}", expanded=True):
            st.write(feedback)

    if st.button("🔄 Novo Treino"):
        st.session_state.estagio = "login"
        st.rerun()
