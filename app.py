import streamlit as st
from groq import Groq
from datetime import datetime, date
import json
import time
import random
import re

# Auto-atualização a cada segundo (pra cronômetro/conexômetro nunca parecerem "parados").
try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(page_title="🧲 CONEXÃO MAGNÉTICA", layout="wide")

GROQ_MODEL = "openai/gpt-oss-120b"
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
adora decorar. Curte cerâmica como hobby (tem um monte de peça torta e desistiu de vender). Gosta de
filme de terror ruim (assiste rindo dos efeitos especiais), odeia futebol mas finge que entende quando
precisa. Café coado, nunca cápsula — isso é quase religião pra ela. Já morou fora (Portugal, 8 meses) e
fala nisso sem parar quando alguém pergunta de viagem. Tem uma irmã mais nova que ela adora e um cachorro
vira-lata chamado Bolota. É direta, tem senso de humor seco/irônico, detesta gente que só fala de trabalho,
e fica visivelmente entediada com conversa rasa — mas quando gosta de alguém, se solta e fica engraçada,
puxa assunto, provoca. Já saiu de encontro ruim várias vezes e ficou cética com clichês de paquera.""",
    },
    "André": {
        "emoji": "👨",
        "descricao": "Homem adulto, comunicativo e descontraído. Gosta de pessoas interessantes, reage bem ao humor, pode provocar e discordar.",
        "pronome": "ele",
        "bio": """29 anos, é fisioterapeuta, trabalha num centro esportivo. Jogou vôlei competitivo até os
22 anos e ainda joga amador aos domingos. Tem um humor autodepreciativo, adora zoar os amigos no grupo do
WhatsApp, é péssimo cozinheiro (vive pedindo comida) mas finge que é chef quando quer impressionar. Gosta
de podcast de true crime, discorda abertamente de opiniões (com boa vontade, não é grosso) e tem uma
irritação real com gente que fica no celular o tempo todo numa conversa. Cresceu numa cidade pequena e se
mudou pra capital há 6 anos — às vezes sente saudade e fala disso. É caloroso, mas não é bobo: nota quando
alguém tá sendo forçado ou decorado, e esfria quando isso acontece. Curte gente que tem opinião própria e
não concorda com tudo só pra agradar.""",
    },
}

DIFFICULTIES = {
    "Paquerador": {"emoji": "🟢", "descricao": "A pessoa virtual demonstra abertura, ajuda a conversa fluir e dá espaço para você desenvolver o assunto."},
    "Galanteador": {"emoji": "🟡", "descricao": "A pessoa virtual é mais exigente: respostas mais curtas, provocações e menos ajuda. Você precisa conduzir mais."},
    "Mestre da Lábia": {"emoji": "🔴", "descricao": "Desafio máximo. A pessoa virtual não facilita, testa sua confiança e pode mudar o rumo da conversa a qualquer momento."},
}

PHASE_GATILHO = {
    "Atração": "gatilhos de atração (despertar interesse inicial, curiosidade, energia)",
    "Conexão": "gatilhos de conexão (aprofundar vínculo, escuta real, evitar modo entrevista)",
    "Sedução": "gatilhos de sedução (tensão, subtexto, confiança, saber avançar e recuar)",
}
PHASE_DIFFICULTY = {"Atração": "Paquerador", "Conexão": "Galanteador", "Sedução": "Mestre da Lábia"}
RANK_AFTER_PHASE = {"Atração": "Paquerador", "Conexão": "Galanteador", "Sedução": "Mestre da Lábia"}
RANK_ORDER = ["Aspirante", "Paquerador", "Galanteador", "Mestre da Lábia"]
RANK_STYLE = {
    "Aspirante": {"emoji": "⚪", "badge": "badge"},
    "Paquerador": {"emoji": "🟢", "badge": "badge-verde"},
    "Galanteador": {"emoji": "🟡", "badge": "badge-amarelo"},
    "Mestre da Lábia": {"emoji": "🔴", "badge": "badge-vermelho"},
}
PASS_THRESHOLD = 60

CENARIOS_ABERTURA = [
    "fila de um café badalado, esperando o pedido",
    "festa de aniversário de um amigo em comum, perto da mesa de bebidas",
    "sala de espera de um evento/workshop que estava lotado",
    "parque, ambos parados vendo alguém tentando controlar um cachorro solto",
    "corredor de uma livraria, os dois mexendo na mesma prateleira",
    "show ao ar livre, esperando a banda começar",
    "loja de discos vasculhando a mesma caixa de vinil",
    "cozinha de um workshop culinário, times misturados",
    "elevador que atrasou muito pra chegar",
    "mesa comunitária lotada de um bar, únicos dois lugares vagos são lado a lado",
]

# ─────────────────────────────────────────────
# ESTILO CSS
# ─────────────────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp { background-color:#F8F9FA; font-family:'Inter',sans-serif; }
    [data-testid="stSidebar"] { display:none; }

    .stTextInput>div>div>input, .stTextArea>div>textarea,
    .stSelectbox>div>div>div, .stNumberInput>div>div>input {
        background-color:#FFFFFF !important; color:#1A1A2E !important;
        border:1px solid #CED4DA !important; font-family:'Inter',sans-serif !important;
    }

    .stButton>button {
        width:100%; border-radius:10px; height:3.2em;
        background:linear-gradient(135deg,#ff3d68,#c92a5b) !important; color:white !important;
        font-weight:600; border:none; box-shadow:2px 2px 10px rgba(255,61,104,0.2);
        font-family:'Inter',sans-serif !important; transition:all 0.2s ease;
    }
    .stButton>button:hover { background:linear-gradient(135deg,#c92a5b,#a01e48) !important; transform:translateY(-1px); }
    .stApp .stButton>button, .stApp .stButton>button p,
    .stApp .stButton>button span, .stApp .stButton>button div { color:white !important; }

    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { color:#1A1A2E !important; font-family:'Inter',sans-serif !important; font-weight:700 !important; }
    .stApp p, .stApp label, .stApp span, .stApp div { color:#2B2B33; }

    .card { background:linear-gradient(135deg,#FFFFFF,#F1F3F5); padding:20px; border-radius:14px; border:1px solid #DEE2E6; margin-bottom:14px; }
    .card-pink { background:linear-gradient(135deg,#FFF0F4,#FFE1E9); padding:20px; border-radius:14px; border:1px solid #ff3d68; margin-bottom:14px; }
    .card-purple { background:linear-gradient(135deg,#F3F0FF,#EAE3FF); padding:20px; border-radius:14px; border:1px solid #8B5CF6; margin-bottom:14px; }
    .card-gold { background:linear-gradient(135deg,#FFFAEB,#FFF3CD); padding:20px; border-radius:14px; border:1px solid #F5C542; margin-bottom:14px; }
    .card, .card *, .card-pink, .card-pink *, .card-purple, .card-purple *, .card-gold, .card-gold * { color:#1A1A2E !important; }

    .stat-box { background:#FFFFFF; border-radius:12px; padding:16px; text-align:center; border:1px solid #DEE2E6; }
    .stat-numero { font-size:2em; font-weight:700; color:#ff3d68 !important; }

    .badge { background:#495057; color:white !important; padding:4px 12px; border-radius:20px; font-size:0.78em; font-weight:600; display:inline-block; margin:2px; }
    .badge-verde { background:#059669; color:white !important; padding:4px 12px; border-radius:20px; font-size:0.78em; font-weight:600; display:inline-block; margin:2px; }
    .badge-amarelo { background:#B45309; color:white !important; padding:4px 12px; border-radius:20px; font-size:0.78em; font-weight:600; display:inline-block; margin:2px; }
    .badge-vermelho { background:#ff3d68; color:white !important; padding:4px 12px; border-radius:20px; font-size:0.78em; font-weight:600; display:inline-block; margin:2px; }

    .divider { border:none; height:1px; background:linear-gradient(to right,transparent,#CED4DA,transparent); margin:18px 0; }

    .chat-user { background:#FFFFFF; border:1px solid #CED4DA; border-radius:12px 12px 4px 12px; padding:12px 16px; margin:8px 0; }
    .chat-persona { background:#FFF0F4; border:1px solid #ff3d68; border-radius:4px 12px 12px 12px; padding:12px 16px; margin:8px 0; }
    .chat-user *, .chat-persona * { color:#1A1A2E !important; }

    .painel-colado {
        background:#FFFFFF; border:2px solid #ff3d68; border-radius:12px;
        padding:12px 16px; margin:10px 0 4px 0;
        box-shadow:0 2px 10px rgba(0,0,0,0.08);
    }
    .painel-colado * { color:#1A1A2E !important; }

    [data-testid="stMetricValue"] { color:#1A1A2E !important; }
    [data-testid="stMetricLabel"] { color:#495057 !important; }
    [data-testid="stMetricDelta"] { color:#1A1A2E !important; }
    [data-testid="stChatInput"] {
        background:#FFFFFF !important; border:2px solid #ff3d68 !important; border-radius:14px !important;
        padding:4px 8px !important;
    }
    [data-testid="stChatInput"] textarea {
        background:#FFFFFF !important; color:#1A1A2E !important; border:none !important;
    }
    [data-testid="stChatInput"] textarea::placeholder { color:#868E96 !important; }
    [data-testid="stChatInput"] button { background:#ff3d68 !important; }
    [data-testid="stChatInput"] button svg { fill:white !important; }
    div[data-baseweb="select"] * { color:#1A1A2E !important; }
    div[data-baseweb="select"] > div { background:#FFFFFF !important; border-color:#CED4DA !important; }
    div[data-baseweb="popover"] { background:#FFFFFF !important; }
    div[data-baseweb="popover"] li, div[data-baseweb="popover"] * { color:#1A1A2E !important; }
    [data-testid="stExpander"] { background:#FFFFFF !important; border:1px solid #CED4DA !important; border-radius:10px !important; }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] p { color:#1A1A2E !important; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CACHE & PERSISTÊNCIA
# ─────────────────────────────────────────────
@st.cache_resource
def get_cache_conexao():
    return {"perfis": {}}

_cache = get_cache_conexao()
CHAVES_SALVAR = ['usuario', 'historico_treinos', 'aberturas_usadas']

def gerar_json_sessao() -> str:
    dados = {k: st.session_state.get(k) for k in CHAVES_SALVAR}
    dados['salvo_em'] = datetime.now().strftime('%d/%m/%Y %H:%M')
    return json.dumps(dados, ensure_ascii=False, indent=2, default=str)

def carregar_json_sessao(dados: dict):
    for k in CHAVES_SALVAR:
        if k in dados:
            st.session_state[k] = dados[k]

def salvar_perfil_cache(usuario: str):
    _cache["perfis"][usuario] = {k: st.session_state.get(k) for k in CHAVES_SALVAR}

def carregar_perfil_cache(usuario: str):
    return _cache["perfis"].get(usuario)

# ─────────────────────────────────────────────
# ESTADO INICIAL
# ─────────────────────────────────────────────
defaults = {
    'etapa': "Login", 'usuario': "", 'api_key': "",
    'estagio': "home", 'character': None,
    'phase_index': 0, 'phase_start_time': None, 'phase_seconds': DEFAULT_PHASE_SECONDS,
    'connexometer': 50, 'messages': [], 'interaction_scores': [], 'phase_results': {},
    'phase_message_start': 0, 'phase_coachings': {}, 'plano_final': None,
    'response_pending_since': None, 'response_times': [],
    'current_rank': "Aspirante", 'treino_encerrado': False, 'parou_na_fase': None,
    'cenario_atual': None, 'aberturas_usadas': [],
    'historico_treinos': [], 'last_result': None, 'last_error': None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reset_training(keep_char_diff=False):
    st.session_state.phase_index = 0
    st.session_state.phase_start_time = None
    st.session_state.connexometer = 50
    st.session_state.messages = []
    st.session_state.interaction_scores = []
    st.session_state.phase_results = {}
    st.session_state.phase_message_start = 0
    st.session_state.phase_coachings = {}
    st.session_state.plano_final = None
    st.session_state.response_pending_since = None
    st.session_state.response_times = []
    st.session_state.current_rank = "Aspirante"
    st.session_state.treino_encerrado = False
    st.session_state.parou_na_fase = None
    st.session_state.cenario_atual = None
    if not keep_char_diff:
        st.session_state.character = None
    st.session_state.estagio = "home"

# ─────────────────────────────────────────────
# MOTOR DE IA (GROQ)
# ─────────────────────────────────────────────
def build_system_prompt(character, difficulty, phase):
    char = CHARACTERS[character]
    cenario = st.session_state.cenario_atual or "situação social casual"

    phase_context = {
        "Atração": (
            f"FASE 1 - ATRAÇÃO (testando GATILHOS DE ATRAÇÃO: energia, curiosidade, interesse inicial). "
            f"Vocês acabaram de se conhecer em: {cenario}. O objetivo é despertar interesse inicial. "
            f"Evite parecer entrevista; reaja com leveza, humor e curiosidade genuína."
        ),
        "Conexão": (
            "FASE 2 - CONEXÃO (testando GATILHOS DE CONEXÃO: escuta real, profundidade, vínculo genuíno). "
            "A conversa já está rolando há um tempo. Aprofunde: histórias, personalidade, valores. "
            "IMPORTANTE: se a pessoa fizer perguntas seguidas estilo entrevista, esfrie o tom."
        ),
        "Sedução": (
            "FASE 3 - SEDUÇÃO (testando GATILHOS DE SEDUÇÃO: tensão, subtexto, confiança, avançar/recuar). "
            "Clima com provocação e tensão romântica elegante. Se houver desrespeito ou apressamento, recue."
        ),
    }[phase]

    difficulty_context = {
        "Paquerador": "Nível fácil: seja receptiva(o), ajude a conversa a fluir e dê respostas abertas.",
        "Galanteador": "Nível médio: seja mais exigente. Respostas mais curtas, provoque, mude de assunto.",
        "Mestre da Lábia": "Nível difícil: não facilite nada. Exija confiança, demonstre pouco interesse inicial.",
    }[difficulty]

    return f"""Você é {character}. {char['descricao']}

BIOGRAFIA:
{char['bio']}

Você está numa simulação de treino de paquera. Interprete de forma 100% realista e humana.
NUNCA revele que é IA, nunca dê dicas fora do personagem.

{phase_context}
{difficulty_context}

REGRAS DE NATURALIDADE:
- MENSAGENS CURTAS: Como no WhatsApp real. Respostas curtas (1 frase na maioria das vezes).
- NÃO termine todas mensagens com pergunta.
- Use a BIOGRAFIA para ser específico.
- Discorde quando pertinente, tenha opinião.
- Responda SOMENTE em JSON válido:
{{
  "resposta": "sua fala aqui",
  "avaliacao": {{"naturalidade":50,"confianca":50,"criatividade":50,"conexao":50,"humor":50,"conducao":50}},
  "delta_conexometro": 0
}}"""

def build_opening_prompt(character):
    cenario = st.session_state.cenario_atual or "situação social casual"
    return (
        f"Gere apenas a fala de abertura de {character} para puxar assunto no cenário: {cenario}. "
        f"Curta, direta e natural. Responda em JSON válido."
    )

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

def extract_failed_generation(error):
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        texto = body.get("error", {}).get("failed_generation")
        if texto:
            return texto.strip()
    m = re.search(r"failed_generation['\"]?:\s*['\"](.+?)['\"]\s*[}\]]", str(error), re.DOTALL)
    if m:
        return m.group(1).strip()
    return None

def call_ai(character, difficulty, phase, history, user_message=None, opening=False):
    client = Groq(api_key=st.session_state.api_key)
    system_prompt = build_system_prompt(character, difficulty, phase)

    base_messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        role = "assistant" if m["role"] == "assistant" else "user"
        base_messages.append({"role": role, "content": m["content"]})
    base_messages.append({"role": "user", "content": build_opening_prompt(character) if opening else user_message})

    last_error = None
    for attempt in range(2):
        try:
            messages = list(base_messages)
            kwargs = dict(
                model=GROQ_MODEL, messages=messages, temperature=0.9,
                max_tokens=350, reasoning_effort="low", reasoning_format="hidden",
            )
            if attempt == 0:
                kwargs["response_format"] = {"type": "json_object"}
                completion = client.chat.completions.create(**kwargs)
                raw = completion.choices[0].message.content
            else:
                messages.append({"role": "assistant", "content": "{"})
                kwargs["messages"] = messages
                completion = client.chat.completions.create(**kwargs)
                raw = "{" + (completion.choices[0].message.content or "")

            data = extract_json(raw)
            resposta = (data.get("resposta") or "...").strip()
            avaliacao = data.get("avaliacao", {})
            for k in CRITERIA_WEIGHTS:
                avaliacao[k] = max(0, min(100, int(avaliacao.get(k, 50))))
            delta = max(-15, min(15, int(data.get("delta_conexometro", 0))))
            return resposta, avaliacao, delta

        except Exception as e:
            last_error = e
            texto_salvo = extract_failed_generation(e)
            if texto_salvo:
                st.session_state.last_error = f"(recuperado) {str(e)[:100]}"
                return texto_salvo, {k: 60 for k in CRITERIA_WEIGHTS}, 0
            continue

    st.session_state.last_error = str(last_error)
    return "Eita, deu um nó no meu pensamento... o que você dizia?", {k: 50 for k in CRITERIA_WEIGHTS}, 0

def time_penalty(resp_time):
    if resp_time is None: return 0
    if resp_time > 45: return 12
    if resp_time > 30: return 8
    if resp_time > 15: return 4
    return 0

def generate_coaching(character, phase, phase_messages, scores):
    if not phase_messages:
        return "Nenhuma interação registrada nesta fase para análise."

    conversa_fmt = "\n".join(f"{'Você' if m['role']=='user' else character}: {m['content']}" for m in phase_messages)
    fracos = sorted(scores.items(), key=lambda x: x[1])[:3]
    fortes = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
    fracos_txt = ", ".join(f"{CRITERIA_LABEL[k]} ({int(v)}/100)" for k, v in fracos if v < 70)
    fortes_txt = ", ".join(f"{CRITERIA_LABEL[k]} ({int(v)}/100)" for k, v in fortes)

    try:
        client = Groq(api_key=st.session_state.api_key)
        prompt = f"""Você é um mentor de comunicação social analisando a fase "{phase}" de um treino com {character}.

CONVERSA:
{conversa_fmt}

Pontos mais fracos: {fracos_txt or "Nenhum ponto crítico"}
Pontos fortes: {fortes_txt}

Dê um feedback conciso e prático em Português.
Use o formato:
🔴 O QUE NÃO FUNCIONOU: (Exemplos específicos da conversa)
🟢 O QUE FUNCIONOU: (Exemplos específicos)
💡 PARA SUBIR DE NÍVEL: (Instrução direta)"""

        completion = client.chat.completions.create(
            model=GROQ_MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.6, max_tokens=600, reasoning_effort="low", reasoning_format="hidden",
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        st.session_state.last_error = str(e)
        return "Análise da fase concluída com sucesso."

def generate_plano_final(character, all_phase_coachings, overall, avg_scores):
    fracos = sorted(avg_scores.items(), key=lambda x: x[1])[:3]
    fracos_txt = ", ".join(f"{CRITERIA_LABEL[k]} ({int(v)}/100)" for k, v in fracos)
    resumo_fases = "\n\n".join(f"[{p}]\n{c}" for p, c in all_phase_coachings.items())

    try:
        client = Groq(api_key=st.session_state.api_key)
        prompt = f"""O usuário completou o treino com {character} obtendo nota final {overall}/100.

Análises por fase:
{resumo_fases}

Critérios com menor pontuação: {fracos_txt}

Escreva um Plano de Ação estruturado de evolução:
❌ MOTIVO DO DESEMPENHO
📌 PONTOS CHAVE A CORRIGIR
🎯 EXERCÍCIO PRÁTICO PARA O PRÓXIMO TREINO"""

        completion = client.chat.completions.create(
            model=GROQ_MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=0.6, max_tokens=700, reasoning_effort="low", reasoning_format="hidden",
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        st.session_state.last_error = str(e)
        return "Plano de evolução gerado. Foque nos pontos de melhoria apontados nas fases anteriores."

# ─────────────────────────────────────────────
# FLUXO DAS TELAS
# ─────────────────────────────────────────────

# TELAS DE AUTENTICAÇÃO E INÍCIO
if st.session_state.etapa == "Login":
    st.markdown("<h1>🧲 CONEXÃO MAGNÉTICA</h1>", unsafe_allow_html=True)
    st.markdown("<p>Simulador Avançado de Conversação & Lábia</p>", unsafe_allow_html=True)
    
    with st.form("form_login"):
        nome = st.text_input("Seu Nome / Apelido", value=st.session_state.usuario)
        key = st.text_input("Sua Groq API Key", value=st.session_state.api_key, type="password")
        sub = st.form_submit_button("Entrar no Simulador")
        if sub and nome and key:
            st.session_state.usuario = nome
            st.session_state.api_key = key
            st.session_state.etapa = "App"
            st.rerun()

elif st.session_state.etapa == "App":
    if HAS_AUTOREFRESH and st.session_state.estagio == "treino":
        st_autorefresh(interval=1000, key="refresh_timer")

    # BARRA SUPERIOR
    cols_top = st.columns([4, 1, 1])
    with cols_top[0]:
        st.markdown(f"**Usuário:** {st.session_state.usuario} | **Rank:** {st.session_state.current_rank}")
    with cols_top[1]:
        if st.button("💾 Salvar Perfil"):
            salvar_perfil_cache(st.session_state.usuario)
            st.toast("Perfil salvo no cache!")
    with cols_top[2]:
        if st.button("🚪 Sair"):
            st.session_state.etapa = "Login"
            st.rerun()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # 1. TELA PRINCIPAL (HOME)
    if st.session_state.estagio == "home":
        st.subheader("Escolha com quem deseja treinar:")
        col_char1, col_char2 = st.columns(2)
        
        for idx, (c_name, c_data) in enumerate(CHARACTERS.items()):
            col = col_char1 if idx == 0 else col_char2
            with col:
                st.markdown(f"<div class='card-pink'><h3>{c_data['emoji']} {c_name}</h3><p>{c_data['descricao']}</p></div>", unsafe_allow_html=True)
                if st.button(f"Treinar com {c_name}", key=f"btn_{c_name}"):
                    st.session_state.character = c_name
                    st.session_state.cenario_atual = random.choice(CENARIOS_ABERTURA)
                    st.session_state.estagio = "treino"
                    st.session_state.phase_start_time = time.time()
                    
                    # Gerar abertura inicial
                    with st.spinner("Iniciando conversa..."):
                        resp, aval, d_conn = call_ai(c_name, PHASE_DIFFICULTY["Atração"], "Atração", [], opening=True)
                        st.session_state.messages.append({"role": "assistant", "content": resp})
                        st.session_state.connexometer = max(0, min(100, 50 + d_conn))
                    st.rerun()

    # 2. TELA DE SIMULAÇÃO (TREINO)
    elif st.session_state.estagio == "treino":
        fase_atual = PHASES[st.session_state.phase_index]
        diff_atual = PHASE_DIFFICULTY[fase_atual]
        char_atual = st.session_state.character
        
        # Cronômetro
        elapsed = time.time() - st.session_state.phase_start_time if st.session_state.phase_start_time else 0
        remaining = max(0, int(st.session_state.phase_seconds - elapsed))
        mins, secs = divmod(remaining, 60)

        # Header do Painel
        st.markdown(f"""
        <div class='painel-colado'>
            <div style='display:flex; justify-size:space-between; align-items:center;'>
                <span><b>Fase:</b> {PHASE_EMOJI[fase_atual]} {fase_atual} ({diff_atual})</span>
                <span><b>Tempo:</b> {mins:02d}:{secs:02d}</span>
                <span><b>Conexômetro:</b> {st.session_state.connexometer}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Exibição do Histórico
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.messages:
                cls = "chat-user" if msg["role"] == "user" else "chat-persona"
                autor = st.session_state.usuario if msg["role"] == "user" else char_atual
                st.markdown(f"<div class='{cls}'><b>{autor}:</b> {msg['content']}</div>", unsafe_allow_html=True)

        # Encerramento por Tempo
        if remaining <= 0:
            st.warning("O tempo da fase acabou!")
            if st.button("Ver Feedback da Fase"):
                st.session_state.estagio = "feedback_fase"
                st.rerun()

        # Input de Mensagem
        user_input = st.chat_input("Digite sua mensagem...")
        if user_input:
            t_now = time.time()
            resp_time = t_now - st.session_state.response_pending_since if st.session_state.response_pending_since else 0
            st.session_state.response_pending_since = t_now
            
            # Adiciona mensagem do usuário
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Chamada IA
            with st.spinner(f"{char_atual} está digitando..."):
                resp, aval, delta = call_ai(
                    char_atual, diff_atual, fase_atual,
                    st.session_state.messages[:-1], user_message=user_input
                )
            
            # Atualização dos Estados
            penalidade = time_penalty(resp_time)
            st.session_state.connexometer = max(0, min(100, st.session_state.connexometer + delta - penalidade))
            st.session_state.messages.append({"role": "assistant", "content": resp})
            st.session_state.interaction_scores.append(aval)
            
            st.rerun()

        if st.button("Avançar para Avaliação da Fase"):
            st.session_state.estagio = "feedback_fase"
            st.rerun()

    # 3. FEEDBACK DA FASE
    elif st.session_state.estagio == "feedback_fase":
        fase_atual = PHASES[st.session_state.phase_index]
        st.subheader(f"📊 Avaliação da Fase: {fase_atual}")

        # Cálculo de Médias
        scores_fase = st.session_state.interaction_scores[st.session_state.phase_message_start:]
        avg_scores = {}
        for k in CRITERIA_WEIGHTS:
            vals = [s[k] for s in scores_fase if k in s]
            avg_scores[k] = sum(vals)/len(vals) if vals else 50

        p_final_fase = sum(avg_scores[k] * CRITERIA_WEIGHTS[k] for k in CRITERIA_WEIGHTS)
        st.session_state.phase_results[fase_atual] = p_final_fase

        st.markdown(f"### Nota da Fase: **{p_final_fase:.1f} / 100**")
        
        # Gerar Coaching
        if fase_atual not in st.session_state.phase_coachings:
            msgs_fase = st.session_state.messages[st.session_state.phase_message_start:]
            with st.spinner("Analisando interações..."):
                coach_txt = generate_coaching(st.session_state.character, fase_atual, msgs_fase, avg_scores)
                st.session_state.phase_coachings[fase_atual] = coach_txt

        st.markdown(f"<div class='card'>{st.session_state.phase_coachings[fase_atual]}</div>", unsafe_allow_html=True)

        if p_final_fase >= PASS_THRESHOLD:
            st.success("Você atingiu a pontuação mínima para avançar!")
            if st.session_state.phase_index < len(PHASES) - 1:
                if st.button("Ir para Próxima Fase"):
                    st.session_state.phase_index += 1
                    st.session_state.phase_message_start = len(st.session_state.messages)
                    st.session_state.phase_start_time = time.time()
                    st.session_state.current_rank = RANK_AFTER_PHASE[fase_atual]
                    st.session_state.estagio = "treino"
                    st.rerun()
            else:
                if st.button("Ver Resultado Final"):
                    st.session_state.current_rank = "Mestre da Lábia"
                    st.session_state.estagio = "resultado_final"
                    st.rerun()
        else:
            st.error("Desempenho insuficiente para avançar de nível nesta tentativa.")
            if st.button("Ver Plano de Ação Final"):
                st.session_state.estagio = "resultado_final"
                st.rerun()

    # 4. TELA DE RESULTADO FINAL
    elif st.session_state.estagio == "resultado_final":
        st.subheader("🏆 Resumo Final do Treino")
        
        all_scores = st.session_state.interaction_scores
        avg_overall = {}
        for k in CRITERIA_WEIGHTS:
            vals = [s[k] for s in all_scores if k in s]
            avg_overall[k] = sum(vals)/len(vals) if vals else 50
        
        overall_score = sum(avg_overall[k] * CRITERIA_WEIGHTS[k] for k in CRITERIA_WEIGHTS)
        
        st.markdown(f"## Rank Alcançado: {st.session_state.current_rank}")
        st.markdown(f"### Nota Geral: **{overall_score:.1f} / 100**")

        if not st.session_state.plano_final:
            with st.spinner("Elaborando relatório de evolução..."):
                st.session_state.plano_final = generate_plano_final(
                    st.session_state.character,
                    st.session_state.phase_coachings,
                    int(overall_score),
                    avg_overall
                )

        st.markdown(f"<div class='card-gold'>{st.session_state.plano_final}</div>", unsafe_allow_html=True)

        if st.button("Iniciar Novo Treino"):
            reset_training()
            st.rerun()
