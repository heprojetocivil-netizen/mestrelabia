import streamlit as st
from groq import Groq
from datetime import datetime, date
import json
import time
import random

# ─────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(page_title="🧲 CONEXÃO MAGNÉTICA", layout="wide")

GROQ_MODEL = "openai/gpt-oss-120b"  # llama-3.3-70b-versatile foi desligado pela Groq em 16/08/2026
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

# Cada fase testa um "gatilho" diferente, com dificuldade crescente, e é um GATE:
# só passa pra próxima se atingir a nota de corte da fase.
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
PASS_THRESHOLD = 60  # nota mínima na fase pra passar de nível

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

    .stApp { background-color:#0E0E14; font-family:'Inter',sans-serif; }
    [data-testid="stSidebar"] { display:none; }

    .stTextInput>div>div>input, .stTextArea>div>textarea,
    .stSelectbox>div>div>div, .stNumberInput>div>div>input {
        background-color:#1A1C24 !important; color:#F5F5F5 !important;
        border:1px solid #33313D !important; font-family:'Inter',sans-serif !important;
    }

    .stButton>button {
        width:100%; border-radius:10px; height:3.2em;
        background:linear-gradient(135deg,#ff3d68,#c92a5b) !important; color:white !important;
        font-weight:600; border:none; box-shadow:2px 2px 10px rgba(255,61,104,0.25);
        font-family:'Inter',sans-serif !important; transition:all 0.2s ease;
    }
    .stButton>button:hover { background:linear-gradient(135deg,#c92a5b,#a01e48) !important; transform:translateY(-1px); }
    .stApp .stButton>button, .stApp .stButton>button p,
    .stApp .stButton>button span, .stApp .stButton>button div { color:white !important; }

    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { color:#F5F5F5 !important; font-family:'Inter',sans-serif !important; font-weight:700 !important; }
    .stApp p, .stApp label, .stApp span, .stApp div { color:#E8E8EC; }

    .card { background:linear-gradient(135deg,#1A1C24,#20222C); padding:20px; border-radius:14px; border:1px solid #33313D; margin-bottom:14px; }
    .card-pink { background:linear-gradient(135deg,#2A1520,#3A1828); padding:20px; border-radius:14px; border:1px solid #ff3d68; margin-bottom:14px; }
    .card-purple { background:linear-gradient(135deg,#1E1A2E,#241E3A); padding:20px; border-radius:14px; border:1px solid #8B5CF6; margin-bottom:14px; }
    .card-gold { background:linear-gradient(135deg,#2A2416,#332B18); padding:20px; border-radius:14px; border:1px solid #F5C542; margin-bottom:14px; }

    .stat-box { background:#1A1C24; border-radius:12px; padding:16px; text-align:center; border:1px solid #33313D; }
    .stat-numero { font-size:2em; font-weight:700; color:#ff3d68 !important; }

    .badge { background:#33313D; color:white !important; padding:4px 12px; border-radius:20px; font-size:0.78em; font-weight:600; display:inline-block; margin:2px; }
    .badge-verde { background:#059669; color:white !important; padding:4px 12px; border-radius:20px; font-size:0.78em; font-weight:600; display:inline-block; margin:2px; }
    .badge-amarelo { background:#B45309; color:white !important; padding:4px 12px; border-radius:20px; font-size:0.78em; font-weight:600; display:inline-block; margin:2px; }
    .badge-vermelho { background:#ff3d68; color:white !important; padding:4px 12px; border-radius:20px; font-size:0.78em; font-weight:600; display:inline-block; margin:2px; }

    .divider { border:none; height:1px; background:linear-gradient(to right,transparent,#33313D,transparent); margin:18px 0; }

    .chat-user { background:#1A1C24; border:1px solid #33313D; border-radius:12px 12px 4px 12px; padding:12px 16px; margin:8px 0; }
    .chat-persona { background:#20161E; border:1px solid #ff3d68; border-radius:4px 12px 12px 12px; padding:12px 16px; margin:8px 0; }

    .disclaimer { background:#1A1C24; border:1px solid #33313D; border-radius:10px; padding:10px 14px; font-size:0.82em; color:#B8B8C0 !important; margin-top:10px; }
    .disclaimer * { color:#B8B8C0 !important; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CACHE (perfis salvos por sessão do servidor)
# ─────────────────────────────────────────────
@st.cache_resource
def get_cache_conexao():
    return {"perfis": {}}

_cache = get_cache_conexao()

CHAVES_SALVAR = [
    'usuario', 'historico_treinos', 'aberturas_usadas',
]

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

def perfis_salvos() -> list:
    return list(_cache["perfis"].keys())

def carregar_perfil_cache(usuario: str):
    return _cache["perfis"].get(usuario)

# ─────────────────────────────────────────────
# ESTADO INICIAL
# ─────────────────────────────────────────────
defaults = {
    'etapa': "Login", 'usuario': "", 'api_key': "",
    'estagio': "home",
    'character': None,
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
            "A conversa já está rolando há um tempo. Aprofunde: histórias, personalidade, valores, coisas "
            "que apaixonam ou irritam. IMPORTANTE: se a pessoa ficar fazendo pergunta atrás de pergunta "
            "feito entrevista, esfrie um pouco (respostas mais curtas, menos entusiasmo)."
        ),
        "Sedução": (
            "FASE 3 - SEDUÇÃO (testando GATILHOS DE SEDUÇÃO: tensão, subtexto, confiança, avançar/recuar "
            "no momento certo). O clima pode ficar mais leve, provocador e com mais tensão romântica, "
            "SEMPRE de forma sutil, elegante e com bom gosto (nada explícito ou vulgar). Use subtexto, "
            "provocações charmosas, brincadeiras. Se a pessoa for grosseira, apressada ou tentar "
            "sexualizar de forma precoce/deselegante, demonstre desconforto e recue."
        ),
    }[phase]

    difficulty_context = {
        "Paquerador": "Nível fácil: seja receptiva(o), ajude a conversa a fluir, dê respostas com mais detalhes e abra ganchos fáceis.",
        "Galanteador": "Nível médio: seja mais seletiva(o). Responda de forma mais curta às vezes, provoque, mude de assunto ocasionalmente.",
        "Mestre da Lábia": "Nível difícil: não facilite nada. Seja exigente, teste a confiança da pessoa, demonstre pouco interesse inicial.",
    }[difficulty]

    return f"""Você é {character}. {char['descricao']}

BIOGRAFIA (use esses detalhes pra dar respostas reais e específicas, não genéricas):
{char['bio']}

Você está numa simulação de treino de conversação social/paquera. O usuário tenta puxar e conduzir a
conversa com você. Interprete {character} de forma 100% realista e humana — NUNCA revele que é IA,
NUNCA dê dicas, NUNCA avalie a resposta da pessoa em voz alta, NUNCA fale como professor(a) ou coach.
Você é só {char['pronome']}, uma pessoa normal numa conversa por mensagem.

{phase_context}

{difficulty_context}

REGRAS DE NATURALIDADE (o mais importante — sua resposta NUNCA pode soar como chatbot):
- VARIE O TAMANHO das mensagens sem padrão fixo: às vezes uma frase curta e seca, às vezes duas ou três
  frases emendadas, às vezes só uma reação ("kkkkk para" / "sério?" / "não acredito"). Nunca todas as
  respostas do mesmo tamanho.
- NÃO termine toda mensagem com uma pergunta. Pessoas de verdade às vezes só comentam, discordam, mudam
  de assunto ou soltam uma opinião sem perguntar nada de volta.
- Use a BIOGRAFIA para responder com detalhes concretos e específicos (nomes, lugares, memórias, opiniões
  reais) em vez de generalidades vagas tipo "gosto de viajar" ou "curto música". Errado: "adoro viajar,
  é muito bom conhecer lugares novos". Certo: "fui pra Portugal um tempo, morei 8 meses lá, até hoje
  sinto falta de um pastel de nata específico de uma padaria em Lisboa".
- TENHA OPINIÃO PRÓPRIA. Discorde às vezes, mesmo que gentilmente. Não concorde com tudo que o usuário
  disser só pra ser agradável — isso é o que faz soar falso/servil, tipo assistente.
- PUXE O FIO da conversa: referencie algo que o próprio {"ela" if char['pronome']=='ela' else 'ele'}
  mesma disse antes, ou algo que o usuário falou 2-3 mensagens atrás, como uma pessoa real faria.
- Escreva como mensagem de texto real do dia a dia: contrações, gírias naturais do português do Brasil,
  pontuação solta às vezes (reticências, sem ponto final em frase curta), mas SEM exagerar em erros de
  português a ponto de ficar caricato.
- EVITE clichês de chatbot: nunca escreva "que interessante!", "conte-me mais sobre isso", "adorei saber
  disso", "isso é muito legal". Reaja como gente de verdade reage: rindo, discordando, achando engraçado,
  ficando surpreso, mudando de assunto abruptamente às vezes.
- Emojis com moderação, só quando fizer sentido — não em toda mensagem.
- É permitido demonstrar tédio, distração, ou responder de forma mais seca se o usuário estiver sendo
  genérico, forçado ou repetitivo — isso é realista, não falha do personagem.

CONTINUIDADE ATÉ O FINAL (isso vale IGUALMENTE para Rafaela e para André, sem exceção):
- Essas regras de naturalidade valem da PRIMEIRA à ÚLTIMA mensagem das 15 minutos de conversa (as 3
  fases inteiras), não só no começo. É comum IA "esfriar" e ficar mais genérica/robótica conforme a
  conversa fica mais longa — isso NÃO pode acontecer aqui. Na última troca da fase de Sedução você
  precisa soar tão espontâneo, específico e com opinião própria quanto na primeira mensagem da fase
  de Atração.
- Isso não significa ficar mais fácil ou mais "gente boa" com o tempo — o nível de exigência da
  dificuldade ({difficulty}) continua valendo até o fim. Significa que, seja a resposta calorosa ou
  fria, ela precisa soar como uma PESSOA real reagindo, nunca como um assistente ficando "em modo
  seguro" ou devolvendo respostas cada vez mais curtas e vagas por cautela.
- Na fase de Sedução em especial: manter bom gosto (regra abaixo) NÃO é desculpa para ficar evasivo,
  monossilábico ou impessoal. Dá pra ter tensão, provocação e personalidade mantendo a elegância —
  isso é atuação de personagem, não geração de conteúdo de risco.

IMPROVISO TOTAL — SEM REPETIÇÃO:
- Esta conversa tem que ser 100% original e improvisada, como se {character} estivesse tendo essa
  conversa pela primeira vez na vida. NUNCA reutilize frases prontas, piadas, comparações ou aberturas
  genéricas — cada treino do usuário é um "novo encontro" diferente, com outro clima, outro assunto,
  outro jeito de reagir.
- Aja como uma pessoa real improvisando no momento: pense em algo específico da cena/cenário descrita e
  reaja a isso, em vez de cair num roteiro decorado.

REGRAS DE CONTEÚDO (inegociáveis):
- Mantenha tudo com bom gosto: flerte, tensão e humor são bem-vindos, conteúdo sexual explícito NUNCA.
- Nunca inclua meta-comentários, notas, dicas ou explicações fora do personagem.
- Respostas curtas a médias, como mensagens reais de conversa (1 a 4 frases, variando).

Depois da resposta em personagem, avalie internamente (NÃO aparece pro usuário) a última mensagem da
pessoa, de 0 a 100 em: naturalidade, confianca, criatividade, conexao (curiosidade/escuta, evita
"modo entrevista"), humor, conducao (leitura de clima, avançar/recuar na hora certa).

Calcule também "delta_conexometro": inteiro entre -15 e 15 (quanto sua percepção mudou com essa troca).

Responda SOMENTE em JSON válido, sem markdown, sem crases, formato exato:
{{
  "resposta": "sua fala em personagem aqui",
  "avaliacao": {{"naturalidade":0,"confianca":0,"criatividade":0,"conexao":0,"humor":0,"conducao":0}},
  "delta_conexometro": 0
}}"""


def build_opening_prompt(character):
    cenario = st.session_state.cenario_atual or "situação social casual"
    aberturas_anteriores = st.session_state.get('aberturas_usadas', [])[-5:]
    bloqueio = ""
    if aberturas_anteriores:
        lista = " | ".join(f'"{a}"' for a in aberturas_anteriores)
        bloqueio = (
            f"\n\nNÃO repita, nem se aproxime, destas aberturas já usadas em treinos anteriores: {lista}. "
            f"Crie algo genuinamente diferente."
        )
    return (
        f"Gere apenas a fala de abertura de {character} pra puxar assunto com o usuário pela primeira vez, "
        f"no seguinte cenário: {cenario}. Use um detalhe específico da BIOGRAFIA ou do cenário pra tornar a "
        f"abertura natural e não genérica — nada de 'oi, tudo bem?'. Curta, direta, com uma pitada de "
        f"personalidade ou humor, que já convide a uma resposta interessante.{bloqueio} Use 0 em todos os "
        f"critérios de avaliação e delta_conexometro 0. Responda no formato JSON de sempre."
    )


def extract_json(raw_text):
    """Parser resistente: o gpt-oss às vezes vaza texto de raciocínio antes/depois do JSON,
    mesmo com reasoning_format='hidden'. Isola o bloco {...} mais externo antes de decodificar."""
    raw_text = (raw_text or "").strip()
    try:
        return json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw_text[start:end + 1])
        raise


def call_ai(character, difficulty, phase, history, user_message=None, opening=False):
    try:
        client = Groq(api_key=st.session_state.api_key)
        system_prompt = build_system_prompt(character, difficulty, phase)

        n_trocas = sum(1 for m in history if m["role"] == "user")
        if n_trocas > 0:
            system_prompt += (
                f"\n\nLEMBRETE DE CONTINUIDADE: vocês já trocaram {n_trocas} mensagens nessa conversa. "
                f"Continue soando tão espontâneo, específico e cheio de personalidade quanto na primeira "
                f"mensagem — não fique mais genérico, mais curto ou mais impessoal só porque a conversa "
                f"está avançando."
            )

        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            role = "assistant" if m["role"] == "assistant" else "user"
            messages.append({"role": role, "content": m["content"]})
        messages.append({"role": "user", "content": build_opening_prompt(character) if opening else user_message})

        completion = client.chat.completions.create(
            model=GROQ_MODEL, messages=messages, temperature=0.9,
            max_tokens=800, response_format={"type": "json_object"},
            reasoning_effort="low", reasoning_format="hidden",
        )
        data = extract_json(completion.choices[0].message.content)
        resposta = (data.get("resposta") or "...").strip()
        avaliacao = data.get("avaliacao", {})
        for k in CRITERIA_WEIGHTS:
            avaliacao[k] = max(0, min(100, int(avaliacao.get(k, 50))))
        delta = max(-15, min(15, int(data.get("delta_conexometro", 0))))
        return resposta, avaliacao, delta
    except Exception as e:
        st.session_state.last_error = str(e)
        return "Hmm, deixa eu pensar melhor no que dizer... me conta mais?", {k: 50 for k in CRITERIA_WEIGHTS}, 0


def time_penalty(resp_time):
    """Conexômetro inteligente: quem demora demais pra responder perde pontos,
    além da penalidade natural de uma resposta fraca."""
    if resp_time is None:
        return 0
    if resp_time > 45:
        return 12
    if resp_time > 30:
        return 8
    if resp_time > 15:
        return 4
    return 0


def generate_coaching(character, phase, phase_messages, scores):
    """Gera feedback específico e instrutivo, citando a própria conversa do usuário."""
    if not phase_messages:
        return "Você não respondeu nesta fase, então não há o que analisar ainda."

    conversa_fmt = "\n".join(
        f"{'Você' if m['role']=='user' else character}: {m['content']}" for m in phase_messages
    )

    fracos = sorted(scores.items(), key=lambda x: x[1])[:3]
    fortes = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
    fracos_txt = ", ".join(f"{CRITERIA_LABEL[k]} ({int(v)}/100)" for k, v in fracos if v < 70)
    fortes_txt = ", ".join(f"{CRITERIA_LABEL[k]} ({int(v)}/100)" for k, v in fortes)

    try:
        client = Groq(api_key=st.session_state.api_key)
        prompt = f"""Você é um coach de comunicação e sedução experiente, analisando o desempenho de um usuário
na fase "{phase}" de um treino de conversação com {character}.

CONVERSA DESTA FASE:
{conversa_fmt}

Critérios em que ele foi mais fraco: {fracos_txt or "nenhum crítico"}
Critérios em que ele foi mais forte: {fortes_txt}

Escreva um feedback DIRETO, ESPECÍFICO e INSTRUTIVO em português do Brasil. O objetivo é ENSINAR, não
elogiar vazio. Se houver pontos fracos, cite pelo menos 2-3 exemplos REAIS de falas dele nesta conversa
onde o problema apareceu, explique especificamente o que deu errado, e diga o que ele deveria ter feito
no lugar. Se ele foi bem, também aponte rapidamente o que funcionou e por quê (com exemplo real).

FORMATO (use exatamente esses marcadores, sem enrolação):
Se houve pontos fracos:
🔴 O QUE NÃO FUNCIONOU:
1. [Situação real da conversa] → [por que isso é um problema] → [o que fazer diferente]
2. [...]
3. [...] (se aplicável)

🟢 O QUE FUNCIONOU:
[1-2 frases citando um exemplo real]

Se ele foi bem em tudo (sem pontos abaixo de 70):
🟢 O QUE FUNCIONOU:
[2-3 exemplos reais específicos do que ele fez certo]

💡 PARA SUBIR AINDA MAIS DE NÍVEL:
[1-2 sugestões de refinamento]

Seja direto, sem rodeios, sem frases motivacionais genéricas. Máximo 180 palavras."""

        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=700,
            reasoning_effort="low", reasoning_format="hidden",
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        st.session_state.last_error = str(e)
        return "Não foi possível gerar o feedback detalhado desta vez."


def generate_plano_final(character, all_phase_coachings, overall, avg_scores):
    """Consolida um plano de ação quando a pessoa não atinge Galanteador (60+)."""
    fracos = sorted(avg_scores.items(), key=lambda x: x[1])[:3]
    fracos_txt = ", ".join(f"{CRITERIA_LABEL[k]} ({int(v)}/100)" for k, v in fracos)
    resumo_fases = "\n\n".join(f"[{p}]\n{c}" for p, c in all_phase_coachings.items())

    try:
        client = Groq(api_key=st.session_state.api_key)
        prompt = f"""O usuário terminou um treino de conversação com {character} e ficou com nota final {overall}/100
(abaixo de 60, ou seja, não passou do nível Paquerador desta vez).

Feedback já dado em cada fase:
{resumo_fases}

Critérios mais fracos no geral: {fracos_txt}

Escreva um resumo INSTRUTIVO e DIRETO em português explicando por que ele não passou desta vez e o que
fazer no próximo treino. Sem enrolação, sem elogio vazio — o objetivo é fazer ele evoluir de verdade.

FORMATO:
❌ POR QUE VOCÊ NÃO PASSOU DESTA VEZ:
1. [motivo concreto 1, baseado no que aconteceu]
2. [motivo concreto 2]
3. [motivo concreto 3, se aplicável]

🎯 PLANO PARA O PRÓXIMO TREINO:
1. [ação concreta 1]
2. [ação concreta 2]
3. [ação concreta 3]

Máximo 150 palavras."""
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=650,
            reasoning_effort="low", reasoning_format="hidden",
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        st.session_state.last_error = str(e)
        return "Não foi possível gerar o plano de ação desta vez."


# ─────────────────────────────────────────────
# CÁLCULOS
# ─────────────────────────────────────────────
def weighted_score(avaliacao):
    return sum(avaliacao[k] * CRITERIA_WEIGHTS[k] for k in CRITERIA_WEIGHTS)

def average_scores(lista):
    if not lista:
        return {k: 60 for k in CRITERIA_WEIGHTS}
    return {k: sum(a[k] for a in lista) / len(lista) for k in CRITERIA_WEIGHTS}

def classify_level(score):
    if score >= 85: return "Mestre da Lábia"
    if score >= 60: return "Galanteador"
    return "Paquerador"

def generate_profile(avg_scores):
    ranked = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
    top2 = {ranked[0][0], ranked[1][0]}
    profiles = [
        ({"naturalidade", "conexao"}, "😎 O Comunicador Natural", "Você demonstra facilidade para criar conversas espontâneas e genuínas. Para evoluir, trabalhe em criar mais tensão e conduzir a interação com mais intenção."),
        ({"conexao", "conducao"}, "🧠 O Observador", "Boa capacidade de ouvir e criar conexão real. Precisa assumir mais iniciativa e ousar mais nos momentos certos."),
        ({"humor", "criatividade"}, "🔥 O Provocador", "Excelente humor e ousadia. Precisa aprender a calibrar melhor a intensidade e ler o clima da outra pessoa."),
        ({"confianca", "conducao"}, "🎯 O Estrategista", "Você conduz a conversa com firmeza e segurança. Pode se soltar mais e deixar a espontaneidade falar mais alto."),
        ({"confianca", "criatividade"}, "⚡ O Espontâneo", "Suas respostas surpreendem e mostram autoconfiança real. Trabalhe em aprofundar a conexão emocional."),
    ]
    for keys, title, desc in profiles:
        if keys & top2:
            return title, desc
    return "🌱 O Aprendiz Promissor", "Você está desenvolvendo suas bases de conversação. Continue treinando."


# ─────────────────────────────────────────────
# COMPONENTES DE UI
# ─────────────────────────────────────────────
def connexometer_bar(value):
    value = max(0, min(100, value))
    if value >= 80:
        color, status = "#ff3d68", "🔥 A conversa está muito boa."
    elif value >= 50:
        color, status = "#F5C542", "⚠️ A conexão está estável."
    else:
        color, status = "#4aa8ff", "❄️ A conexão está esfriando."
    st.markdown(f"""
        <div style="margin-bottom:4px; font-weight:600;">❤️ CONEXÔMETRO — {int(value)}%</div>
        <div style="background:#20222C; border-radius:8px; height:22px; width:100%; overflow:hidden;">
            <div style="background:{color}; width:{value}%; height:100%; transition: width 0.4s;"></div>
        </div>
        <div style="font-size:0.85em; margin-top:4px; opacity:0.85;">{status}</div>
    """, unsafe_allow_html=True)

def phase_timer():
    elapsed = time.time() - st.session_state.phase_start_time
    remaining = max(0, st.session_state.phase_seconds - elapsed)
    mins, secs = divmod(int(remaining), 60)
    st.markdown(f"⏱️ **{mins:02d}:{secs:02d}**")
    return remaining

def barra_salvar():
    salvar_perfil_cache(st.session_state.usuario)
    nome_usuario = st.session_state.usuario.lower().replace(' ', '_') or 'meu_treino'
    total = len(st.session_state.historico_treinos)
    col_info, col_btn = st.columns([4, 2])
    with col_info:
        st.markdown(
            f"<div class='disclaimer'>💾 <strong>Antes de sair, salve seus dados no computador.</strong><br>"
            f"<span>{total} treino(s) concluído(s)</span></div>", unsafe_allow_html=True
        )
    with col_btn:
        st.download_button("💾 SALVAR MEUS DADOS (.json)", data=gerar_json_sessao(),
            file_name=f"conexao_magnetica_{nome_usuario}.json", mime="application/json", use_container_width=True)
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ============================================================
# TELA: LOGIN
# ============================================================
if st.session_state.etapa == "Login":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🧲 CONEXÃO MAGNÉTICA")
        st.markdown("**Mestre da Lábia — treino de conversação social com IA**")
        st.markdown(
            "<p style='font-style:italic;'>Você não vai aprender o que dizer. Vai aprender a conversar.</p>",
            unsafe_allow_html=True,
        )
        st.write(
            "Um treinamento interativo onde você conversa com uma pessoa virtual em situações reais "
            "e desenvolve sua capacidade de criar atração, conexão e sedução."
        )
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        perfis = perfis_salvos()
        if perfis:
            st.markdown("#### 🧲 Clique para acessar seus dados")
            chave_rapida = st.text_input("🔑 Sua Chave API da Groq:", type="password", key="chave_rapida")
            for nome_p in perfis:
                dados_p = carregar_perfil_cache(nome_p)
                total_p = len(dados_p.get('historico_treinos', [])) if dados_p else 0
                if st.button(f"🧲 {nome_p}  —  {total_p} treino(s)", key=f"perfil_{nome_p}", use_container_width=True):
                    if not chave_rapida.strip():
                        st.warning("Cole sua chave API acima antes de entrar.")
                    else:
                        st.session_state.usuario = nome_p
                        st.session_state.api_key = chave_rapida
                        carregar_json_sessao(dados_p)
                        st.session_state.etapa = "App"
                        st.rerun()
            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            st.markdown("**Ou entre com outro nome:**")

        nome = st.text_input("Seu Nome:", key="input_nome_login")
        chave = st.text_input("Sua Chave API da Groq:", type="password", key="chave_nova")

        if not perfis:
            st.markdown(
                "<div class='disclaimer'>📥 <strong>Seus dados sumiram?</strong> "
                "Selecione abaixo o arquivo <strong>.json</strong> que você salvou antes.</div>",
                unsafe_allow_html=True,
            )
            arq_login = st.file_uploader("Carregar meus dados salvos (.json):", type=["json"], key="upload_login")
        else:
            arq_login = None

        dados_login = None
        if arq_login is not None:
            try:
                dados_login = json.load(arq_login)
                st.success(f"✅ Dados de **{dados_login.get('usuario','')}** reconhecidos! Clique em Entrar.")
            except Exception:
                st.error("Arquivo inválido.")

        if st.button("🔥 ENTRAR NO TREINAMENTO"):
            if nome and chave:
                st.session_state.usuario = nome
                st.session_state.api_key = chave
                if dados_login:
                    carregar_json_sessao(dados_login)
                st.session_state.etapa = "App"
                st.rerun()
            else:
                st.warning("Preencha nome e chave API.")

        st.markdown(
            "🔑 Não tem chave Groq? Crie grátis em "
            "<a href='https://console.groq.com/keys' target='_blank' style='color:#ff3d68;font-weight:600;'>console.groq.com/keys</a>",
            unsafe_allow_html=True,
        )

# ============================================================
# TELA: APP
# ============================================================
elif st.session_state.etapa == "App":

    barra_salvar()

    col_titulo, col_sair = st.columns([4, 1])
    with col_titulo:
        st.markdown(f"### 🧲 Olá, {st.session_state.usuario}!")
    with col_sair:
        if st.button("🚪 Sair"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    nav = st.columns(3)
    if nav[0].button("🏠 Início", use_container_width=True):
        reset_training()
        st.rerun()
    if nav[1].button("🔥 Treinar", use_container_width=True):
        st.session_state.estagio = "training" if st.session_state.character else "character"
        st.rerun()
    if nav[2].button("📊 Meu Desempenho", use_container_width=True):
        st.session_state.estagio = "performance"
        st.rerun()

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    estagio = st.session_state.estagio

    # ---------------- HOME ----------------
    if estagio == "home":
        st.markdown(
            "<h2 style='text-align:center;'>🧲 CONEXÃO MAGNÉTICA</h2>"
            "<h5 style='text-align:center; opacity:0.8;'>Mestre da Lábia</h5>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align:center; font-style:italic;'>Você não vai aprender o que dizer. "
            "Vai aprender a conversar.</p>", unsafe_allow_html=True,
        )
        st.write(
            "Você começa como **⚪ Aspirante**. Cada fase testa um gatilho diferente e é um teste de "
            "verdade: só sobe de nível se passar."
        )
        st.markdown(f"""
        <div class='card'>
        🔥 <strong>Fase 1 — Atração</strong> (fácil) → passa e vira <span class='badge-verde'>🟢 Paquerador</span><br>
        💫 <strong>Fase 2 — Conexão</strong> (médio) → passa e vira <span class='badge-amarelo'>🟡 Galanteador</span><br>
        ❤️ <strong>Fase 3 — Sedução</strong> (difícil) → passa e vira <span class='badge-vermelho'>🔴 Mestre da Lábia</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        col = st.columns([1, 2, 1])[1]
        with col:
            if st.button("🔥 COMEÇAR TREINAMENTO", use_container_width=True):
                reset_training(keep_char_diff=False)
                st.session_state.estagio = "character"
                st.rerun()

        if st.session_state.historico_treinos:
            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            st.markdown("### 🕐 Últimos treinos")
            for item in reversed(st.session_state.historico_treinos[-4:]):
                rk = RANK_STYLE.get(item.get('rank_final', 'Aspirante'), RANK_STYLE['Aspirante'])
                st.markdown(
                    f"<div class='card'><span class='badge'>{item['personagem']}</span> "
                    f"<span class='{rk['badge']}'>{rk['emoji']} {item.get('rank_final','Aspirante')}</span> "
                    f"<small style='color:#888'>{item['data']}</small><br>Resultado: <strong>{item['overall']}</strong></div>",
                    unsafe_allow_html=True,
                )

    # ---------------- ESCOLHA DE PERSONAGEM ----------------
    elif estagio == "character":
        st.header("🎭 ESCOLHA SEU DESAFIO")
        st.caption("Com quem você vai treinar hoje?")
        cols = st.columns(2)
        for col, (name, info) in zip(cols, CHARACTERS.items()):
            with col:
                st.markdown(f"<div class='card'><h4>{info['emoji']} {name}</h4><p>{info['descricao']}</p></div>", unsafe_allow_html=True)
                if st.button(f"Escolher {name}", key=f"char_{name}", use_container_width=True):
                    st.session_state.character = name
                    reset_training(keep_char_diff=True)
                    st.session_state.cenario_atual = random.choice(CENARIOS_ABERTURA)
                    st.session_state.estagio = "training"
                    st.rerun()

    # ---------------- TREINAMENTO ----------------
    elif estagio == "training":
        if not st.session_state.api_key:
            st.error("Chave da Groq não configurada. Volte ao Login.")
        else:
            phase = PHASES[st.session_state.phase_index]
            character = st.session_state.character
            difficulty = PHASE_DIFFICULTY[phase]

            if st.session_state.phase_start_time is None:
                st.session_state.phase_start_time = time.time()
                if phase == "Atração" and not st.session_state.messages:
                    if not st.session_state.cenario_atual:
                        st.session_state.cenario_atual = random.choice(CENARIOS_ABERTURA)
                    with st.spinner(f"{character} está chegando..."):
                        resposta, _av, _d = call_ai(character, difficulty, phase, [], opening=True)
                    st.session_state.messages.append({"role": "assistant", "content": resposta})
                    st.session_state.response_pending_since = time.time()
                    st.session_state.aberturas_usadas = (st.session_state.aberturas_usadas + [resposta])[-10:]

            rk = RANK_STYLE[st.session_state.current_rank]
            st.markdown(
                f"<h4 style='text-align:center;'>{PHASE_EMOJI[phase]} FASE {st.session_state.phase_index+1} — "
                f"{phase.upper()} <span style='opacity:0.6;font-size:0.6em;'>(testando {PHASE_GATILHO[phase].split('(')[0].strip()})</span></h4>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<p style='text-align:center;'><span class='{rk['badge']}'>{rk['emoji']} {st.session_state.current_rank}</span> "
                f"<span class='badge'>{DIFFICULTIES[difficulty]['emoji']} nível {difficulty}</span></p>",
                unsafe_allow_html=True,
            )

            t1, t2, t3 = st.columns(3)
            with t1:
                remaining = phase_timer()
            with t2:
                st.markdown(f"💬 **{len(st.session_state.interaction_scores)}** respostas")
            with t3:
                st.markdown(f"{CHARACTERS[character]['emoji']} **{character}**")

            connexometer_bar(st.session_state.connexometer)
            st.markdown("<hr class='divider'>", unsafe_allow_html=True)

            for m in st.session_state.messages:
                css_class = "chat-persona" if m["role"] == "assistant" else "chat-user"
                autor = f"{CHARACTERS[character]['emoji']} {character}" if m["role"] == "assistant" else "🙂 Você"
                st.markdown(f"<div class='{css_class}'><strong>{autor}:</strong><br>{m['content']}</div>", unsafe_allow_html=True)

            if remaining <= 0:
                scores = st.session_state.interaction_scores
                avg = average_scores(scores)
                score = round(weighted_score(avg))
                passou = score >= PASS_THRESHOLD
                st.session_state.phase_results[phase] = {"score": score, "scores": avg, "passou": passou}

                phase_msgs = st.session_state.messages[st.session_state.phase_message_start:]
                with st.spinner("Analisando sua conversa nesta fase..."):
                    coaching = generate_coaching(character, phase, phase_msgs, avg)
                st.session_state.phase_coachings[phase] = coaching

                st.session_state.interaction_scores = []
                st.session_state.estagio = "phase_end"
                st.rerun()

            user_msg = st.chat_input("Digite sua resposta...")
            if user_msg:
                resp_time = None
                if st.session_state.response_pending_since:
                    resp_time = time.time() - st.session_state.response_pending_since
                    st.session_state.response_times.append(resp_time)

                st.session_state.messages.append({"role": "user", "content": user_msg})
                with st.spinner(f"{character} está digitando..."):
                    resposta, avaliacao, delta_qualidade = call_ai(
                        character, difficulty, phase, st.session_state.messages[:-1], user_message=user_msg,
                    )
                st.session_state.messages.append({"role": "assistant", "content": resposta})
                st.session_state.interaction_scores.append(avaliacao)

                # CONEXÔMETRO INTELIGENTE: qualidade da resposta + penalidade por demora
                penalidade = time_penalty(resp_time)
                net = delta_qualidade - penalidade
                st.session_state.connexometer = max(0, min(100, st.session_state.connexometer + net))
                st.session_state.response_pending_since = time.time()

                if penalidade > 0:
                    st.toast(f"⏱️ Demorou {resp_time:.0f}s pra responder: −{penalidade} no conexômetro", icon="⏱️")
                st.toast(f"{'📈' if net >= 0 else '📉'} {'+' if net>=0 else ''}{net} no conexômetro", icon="🧲")
                st.rerun()

            st.caption("A IA está interpretando o personagem em tempo real — quanto mais você demorar, mais o conexômetro esfria.")
            if st.button("🔄 Atualizar cronômetro"):
                st.rerun()

    # ---------------- FIM DE FASE ----------------
    elif estagio == "phase_end":
        phase = PHASES[st.session_state.phase_index]
        result = st.session_state.phase_results.get(phase, {"score": 0, "scores": {}, "passou": False})
        score, scores, passou = result["score"], result["scores"], result["passou"]
        coaching = st.session_state.phase_coachings.get(phase, "")

        st.markdown(f"<h3 style='text-align:center;'>{PHASE_EMOJI[phase]} {phase.upper()} — TESTE CONCLUÍDO</h3>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align:center;'>{score}/100</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; opacity:0.7;'>Nota de corte pra passar: {PASS_THRESHOLD}/100</p>", unsafe_allow_html=True)

        if passou:
            novo_rank = RANK_AFTER_PHASE[phase]
            st.session_state.current_rank = novo_rank
            rk = RANK_STYLE[novo_rank]
            st.markdown(
                f"<div class='card-gold' style='text-align:center;'>"
                f"<h3>🎉 VOCÊ PASSOU!</h3>"
                f"<h2><span class='{rk['badge']}'>{rk['emoji']} Agora você é {novo_rank.upper()}</span></h2>"
                f"</div>", unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='card-pink' style='text-align:center;'>"
                f"<h3>❌ VOCÊ NÃO PASSOU DESTA VEZ</h3>"
                f"<p>Você continua como <span class='{RANK_STYLE[st.session_state.current_rank]['badge']}'>"
                f"{RANK_STYLE[st.session_state.current_rank]['emoji']} {st.session_state.current_rank}</span> — "
                f"não deu pra desbloquear a próxima fase agora.</p>"
                f"</div>", unsafe_allow_html=True,
            )

        st.markdown(f"<div class='card'>{coaching}</div>", unsafe_allow_html=True)
        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        is_last_phase = st.session_state.phase_index >= len(PHASES) - 1
        encerrar_agora = (not passou) or is_last_phase
        label = "🏆 VER RESULTADO FINAL" if encerrar_agora else f"{PHASE_EMOJI[PHASES[st.session_state.phase_index+1]]} CONTINUAR PARA A PRÓXIMA FASE"

        if st.button(label, use_container_width=True, type="primary"):
            if encerrar_agora:
                fases_jogadas = list(st.session_state.phase_results.keys())
                all_scores = [r["scores"] for r in st.session_state.phase_results.values()]
                avg = average_scores(all_scores)
                overall = round(weighted_score(avg))
                entry = {
                    "data": datetime.now().strftime('%d/%m/%Y %H:%M'),
                    "personagem": st.session_state.character,
                    "rank_final": st.session_state.current_rank,
                    "treino_completo": passou and is_last_phase,
                    "parou_na_fase": phase,
                    "overall": overall,
                    "fases": {p: r["score"] for p, r in st.session_state.phase_results.items()},
                    "criterios": avg,
                    "tempo_medio_resposta": (sum(st.session_state.response_times) / len(st.session_state.response_times)) if st.session_state.response_times else None,
                    "interacoes": sum(1 for m in st.session_state.messages if m["role"] == "user"),
                    "conexometro_max": st.session_state.connexometer,
                }
                st.session_state.historico_treinos.append(entry)
                st.session_state.last_result = entry
                st.session_state.treino_encerrado = True
                st.session_state.parou_na_fase = phase

                if not passou:
                    with st.spinner("Montando seu plano de ação..."):
                        st.session_state.plano_final = generate_plano_final(
                            st.session_state.character, st.session_state.phase_coachings, overall, avg,
                        )
                else:
                    st.session_state.plano_final = None

                st.session_state.estagio = "final"
            else:
                st.session_state.phase_index += 1
                st.session_state.phase_start_time = None
                st.session_state.phase_message_start = len(st.session_state.messages)
                st.session_state.estagio = "training"
            st.rerun()

    # ---------------- RESULTADO FINAL ----------------
    elif estagio == "final":
        entry = st.session_state.last_result
        if not entry:
            st.session_state.estagio = "home"
            st.rerun()
        else:
            rank_final = entry.get("rank_final", "Aspirante")
            rk = RANK_STYLE[rank_final]
            overall = entry["overall"]

            if entry.get("treino_completo"):
                st.markdown("<h4 style='text-align:center;'>🏆 TREINO COMPLETO!</h4>", unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<h4 style='text-align:center;'>Parou na fase {entry.get('parou_na_fase','?').upper()}</h4>",
                    unsafe_allow_html=True,
                )
            st.markdown(f"<h1 style='text-align:center; font-size:4em;'>{overall}</h1>", unsafe_allow_html=True)
            st.markdown(
                f"<h3 style='text-align:center;'><span class='{rk['badge']}'>{rk['emoji']} {rank_final.upper()}</span></h3>",
                unsafe_allow_html=True,
            )

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            st.write("#### 📊 Relatório final")
            c1, c2, c3 = st.columns(3)
            c1.metric("🔥 Atração", entry["fases"].get("Atração", "—"))
            c2.metric("💫 Conexão", entry["fases"].get("Conexão", "—"))
            c3.metric("❤️ Sedução", entry["fases"].get("Sedução", "—"))

            c4, c5, c6 = st.columns(3)
            c4.metric("🧲 Conexômetro máx.", f"{entry['conexometro_max']}%")
            tmr = entry["tempo_medio_resposta"]
            c5.metric("⚡ Tempo médio resp.", f"{tmr:.1f}s" if tmr else "-")
            c6.metric("💬 Interações", entry["interacoes"])

            if st.session_state.plano_final:
                st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                st.markdown("#### 🎯 Você não passou desta vez — aqui está o porquê")
                st.markdown(f"<div class='card-pink'>{st.session_state.plano_final}</div>", unsafe_allow_html=True)

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            title, desc = generate_profile(entry["criterios"])
            st.markdown(f"<div class='card-purple'><h4>{title}</h4><p>{desc}</p></div>", unsafe_allow_html=True)

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Jogar Novamente", use_container_width=True):
                    reset_training()
                    st.session_state.estagio = "character"
                    st.rerun()
            with col2:
                if st.button("📊 Meu Desempenho", use_container_width=True):
                    st.session_state.estagio = "performance"
                    st.rerun()

    # ---------------- DESEMPENHO ----------------
    elif estagio == "performance":
        st.header("📊 MEU DESEMPENHO")
        hist = st.session_state.historico_treinos

        if not hist:
            st.info("Você ainda não completou nenhum treinamento.")
        else:
            latest = hist[-1]
            rank_latest = latest.get("rank_final", "Aspirante")
            rk = RANK_STYLE[rank_latest]
            st.markdown(f"**Rank atual:** <span class='{rk['badge']}'>{rk['emoji']} {rank_latest.upper()}</span>", unsafe_allow_html=True)
            st.markdown(f"**Pontuação geral (última sessão):** {latest['overall']}")

            cols = st.columns(3)
            cols[0].metric("🔥 Atração", latest["fases"].get("Atração", "—"))
            cols[1].metric("💫 Conexão", latest["fases"].get("Conexão", "—"))
            cols[2].metric("❤️ Sedução", latest["fases"].get("Sedução", "—"))

            st.write("##### Critérios (última sessão)")
            for k, v in latest["criterios"].items():
                st.write(CRITERIA_LABEL[k])
                st.progress(min(1.0, v / 100))

            st.markdown("<hr class='divider'>", unsafe_allow_html=True)
            st.write("#### 🏆 Minha Evolução")
            scores_over_time = [h["overall"] for h in hist]
            st.line_chart(scores_over_time)

            table_rows = [
                {"Treino": f"#{i+1:02d}", "Resultado": h["overall"], "Personagem": h["personagem"], "Rank": h.get("rank_final", "Aspirante")}
                for i, h in enumerate(hist)
            ]
            st.dataframe(table_rows, use_container_width=True, hide_index=True)

            if len(scores_over_time) >= 2:
                st.markdown(f"📈 **Sua evolução:** {scores_over_time[0]} → {scores_over_time[-1]}")

            dates = sorted({datetime.strptime(h["data"], '%d/%m/%Y %H:%M').date() for h in hist}, reverse=True)
            streak, today = 0, date.today()
            for i, d in enumerate(dates):
                if d.toordinal() == today.toordinal() - i:
                    streak += 1
                else:
                    break
            if streak > 0:
                st.markdown(f"🔥 **Sequência:** você está há **{streak} dia(s)** consecutivo(s) treinando.")

    # rodapé com aviso de erro, se houver
    if st.session_state.last_error:
        with st.expander("⚠️ Última mensagem de erro da IA"):
            st.code(st.session_state.last_error)

# --- RODAPÉ ---
st.markdown(
    "<div style='text-align:center;color:#666;font-size:0.8em;margin-top:60px;'>"
    "🧲 Conexão Magnética — Mestre da Lábia · Treino de conversação com IA (Groq)"
    "</div>", unsafe_allow_html=True
)
