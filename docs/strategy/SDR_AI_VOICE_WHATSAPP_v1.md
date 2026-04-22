# SDR AI VOICE + WHATSAPP — Orkestra Finance Brain

**Versão:** 1.0  
**Data:** 2026-04-08  
**Canais:** WhatsApp + ManyChat  
**Voz:** ElevenLabs (português BR)  
**Status:** Especificação Completa

---

## 🔄 FLUXO COMPLETO

```
[Lead envia WhatsApp]
         ↓
[ManyChat recebe]
         ↓
[Webhook → OpenClaw]
         ↓
┌─────────────────┐
│  CONVERSATION   │
│    ENGINE       │
└────────┬────────┘
         ↓
┌──────────────────────────────────────┐
│  DECISÃO: Texto ou Voz?              │
│  - Primeira interação? → Voz          │
│  - Pergunta simples? → Texto          │
│  - Momento emocional? → Voz           │
│  - Cliente prefere texto? → Texto     │
└──────────────────────────────────────┘
         ↓
┌─────────────────┐     ┌─────────────────┐
│  GERAR TEXTO    │     │  GERAR VOZ      │
│  (IA Gemini)    │     │  (ElevenLabs)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │              ┌────────┴────────┐
         │              │  VOICE LOGIC    │
         │              │  - Tom: amigável│
         │              │  - Velocidade   │
         │              │  - Emoção       │
         │              └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │    ENVIAR WHATSAPP    │
         │    (via ManyChat API) │
         └───────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────┐
│  LEAD QUALIFICATION                  │
│  - Coletar dados                     │
│  - Validar informações               │
│  - Calcular score                    │
└──────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────┐
│  SCORING SYSTEM                      │
│  Tier S/A/B/C/D                     │
│  Prioridade: Critical/High/Med/Low  │
└──────────────────────────────────────┘
         │
         ↓
┌──────────────────────────────────────┐
│  DECISION                            │
│  S/A → Agendar (Google Calendar)     │
│  B   → Continuar conversa            │
│  C/D → Discartar / Nurture           │
└──────────────────────────────────────┘
         │
         ↓
[Atualiza sales_pipeline]
```

---

## 📱 ARQUITETURA WHATSAPP + MANYCHAT

### Configuração ManyChat

```javascript
// Webhook configuration in ManyChat
// Settings → API → Webhooks

const webhookConfig = {
    url: 'https://orkestra.ai/webhook/manychat',
    events: ['user_input', 'user_attribute_change', 'flow_completion'],
    verify_token: process.env.MANYCHAT_VERIFY_TOKEN
};
```

### Fluxo ManyChat

```
[RECEBER MENSAGEM WHATSAPP]
         ↓
[TRIGGER: Novo usuário]
         ↓
[ACTION: HTTP Request]
    URL: https://orkestra.ai/webhook/manychat
    Method: POST
    Headers: {
        "Authorization": "Bearer OPENCLAW_TOKEN",
        "Content-Type": "application/json"
    }
    Body: {
        "user_id": "{{user.id}}",
        "phone": "{{user.phone}}",
        "name": "{{user.first_name}}",
        "message": "{{last_input}}",
        "platform": "whatsapp",
        "timestamp": "{{current_timestamp}}"
    }
         ↓
[AGUARDAR RESPOSTA]
    Timeout: 5 seconds
         ↓
[RESPOSTA RECEBIDA]
         ↓
[IF response.has_voice]
    → Send Voice Message
[ELSE]
    → Send Text Message
```

---

## 🗣️ VOICE LOGIC (Lógica de Voz)

### Quando Usar Áudio vs Texto

| Situação | Formato | Razão |
|----------|---------|-------|
| Primeira interação | 🎤 **Voz** | Mais pessoal, humano |
| Saudação | 🎤 **Voz** | Cria conexão emocional |
| Explicação complexa | 🎤 **Voz** | Fácil de entender |
| Momento de decisão | 🎤 **Voz** | Transmite confiança |
| Dados simples (data, número) | 📝 Texto | Fácil de copiar |
| Confirmação rápida | 📝 Texto | Eficiente |
| Pergunta já respondida | 📝 Texto | Não repetir voz |
| Cliente pediu texto | 📝 Texto | Respeitar preferência |
| Fora horário comercial | 📝 Texto | Silencioso |

### Configuração ElevenLabs

```python
# voice_config.py
ELEVENLABS_CONFIG = {
    "api_key": os.getenv("ELEVENLABS_API_KEY"),
    
    # Voz escolhida: português brasileiro natural
    "voice_id": "pNInz6obpgDQGcFNOJw",  # Adam (ajuste para PT-BR)
    # Alternativas:
    # - "21m00Tcm4TlvDq8ikWAM" # Rachel
    # - "AZnzlk1XvdvUeBnXmlld" # Domi
    
    "model_id": "eleven_multilingual_v2",
    
    # Configurações de voz
    "stability": 0.5,           # 0-1: consistência
    "similarity_boost": 0.75,   # 0-1: clareza
    "style": 0.3,              # 0-1: expressividade
    "use_speaker_boost": True,
    
    # Ajustes de fala
    "speed": 1.0,              # Velocidade
    "pitch": 1.0,              # Tom
    "volume": 1.0,              # Volume
    
    # Emoção baseada no contexto
    "emotions": {
        "greeting": {"style": 0.5, "tone": "warm"},
        "question": {"style": 0.3, "tone": "neutral"},
        "excitement": {"style": 0.8, "tone": "energetic"},
        "empathy": {"style": 0.6, "tone": "soft"},
        "closing": {"style": 0.4, "tone": "professional"}
    }
}
```

### Geração de Voz

```python
import requests
from pathlib import Path

def generate_voice_response(text: str, emotion: str = "neutral") -> str:
    """
    Gera áudio da resposta usando ElevenLabs
    Retorna: URL do áudio no S3/temp
    """
    
    # Aplicar emoção
    config = ELEVENLABS_CONFIG.copy()
    if emotion in config["emotions"]:
        config["style"] = config["emotions"][emotion]["style"]
    
    # Preparar texto (ajustes para português)
    text_optimized = optimize_for_speech(text)
    
    # Chamada API
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{config['voice_id']}",
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": config["api_key"]
        },
        json={
            "text": text_optimized,
            "model_id": config["model_id"],
            "voice_settings": {
                "stability": config["stability"],
                "similarity_boost": config["similarity_boost"],
                "style": config["style"],
                "use_speaker_boost": config["use_speaker_boost"]
            }
        }
    )
    
    if response.status_code == 200:
        # Salvar temporariamente
        audio_path = f"/tmp/voice_{uuid.uuid4()}.mp3"
        with open(audio_path, "wb") as f:
            f.write(response.content)
        
        # Upload para S3 (ou servidor local)
        s3_url = upload_to_s3(audio_path)
        return s3_url
    else:
        # Fallback: retornar texto
        return None

def optimize_for_speech(text: str) -> str:
    """Otimiza texto para fala natural"""
    
    # Quebrar números grandes
    text = re.sub(r'(\d{3,})', lambda m: f"{m.group(1):,}".replace(",", "."), text)
    
    # Expandir abreviações
    replacements = {
        "R$": "reais",
        "km": "quilômetros",
        "h": "horas",
        "min": "minutos",
        "etc": "e assim por diante",
        "vs": "versus"
    }
    
    for abbr, full in replacements.items():
        text = text.replace(f" {abbr} ", f" {full} ")
    
    # Pausas naturais
    text = text.replace("...", ", ")
    text = text.replace("  ", " ")
    
    return text
```

---

## 📱 FORMATO DE MENSAGENS WHATSAPP

### Estrutura de Payload

```json
{
  "platform": "whatsapp",
  "channel": "manychat",
  "user": {
    "id": "whatsapp_5511999999999",
    "phone": "5511999999999",
    "name": "Maria Silva",
    "profile_pic": "https://..."
  },
  "message": {
    "id": "msg_123456",
    "text": "Oi, quero fazer uma festa",
    "type": "text",
    "timestamp": "2026-04-08T17:30:00Z",
    "has_media": false
  },
  "context": {
    "conversation_id": "conv_abc123",
    "session_id": "session_xyz789",
    "turn_number": 1,
    "previous_messages": []
  }
}
```

### Resposta para WhatsApp

```json
{
  "response_type": "voice",
  "message": {
    "text": "Olá Maria! Que bom falar com você. Sou o assistente da Orkestra e vou ajudar a planejar sua festa. Posso fazer algumas perguntas rápidas?",
    "voice_url": "https://orkestra.ai/audio/response_123.mp3",
    "voice_duration": 8.5
  },
  "actions": [],
  "next_expected": "user_response",
  "session_update": {
    "stage": "qualification",
    "turn": 2
  }
}
```

---

## 🤖 CONVERSATION ENGINE

### Estados da Conversa

```
┌─────────┐
│ START   │ → Saudação inicial (sempre em voz)
└────┬────┘
     ↓
┌─────────────┐
│ QUALIFICAÇÃO│ → Perguntas essenciais
│   (etapas)  │    1. Tipo evento
└────┬────────┘    2. Data
     │             3. Convidados
     │             4. Cidade
     │             5. Orçamento
     ↓
┌─────────────┐
│   SCORING   │ → Calcular pontuação
└────┬────────┘
     ↓
┌─────────────┐
│   DECISÃO   │
└────┬────────┘
     │
     ├─ Score S/A → [AGENDAR] → Google Calendar
     │
     ├─ Score B → [CONTINUAR] → Mais informações
     │
     └─ Score C/D → [NURTURE] → Descartar/Guardar
```

### Script de Conversa (Voz)

```
=== SAUDAÇÃO (VOZ) ===
"Olá! Que bom receber sua mensagem. Meu nome é assistente Orkestra 
e vou ajudar você a planejar um evento incrível. Posso fazer 
algumas perguntas rápidas para entender melhor o que você precisa?"

---

=== QUALIFICAÇÃO ===

[PERGUNTA 1 - Tipo]
Texto: "Que tipo de evento você está planejando?"
Voz: "Que legal! Que tipo de evento você está planejando? 
      Pode ser casamento, aniversário, evento corporativo..."
      
[PERGUNTA 2 - Data]
Texto: "Qual data você está pensando?"
Voz: "Perfeito! E qual seria a data ideal para você? 
      Se tiver flexibilidade, me fale também."

[PERGUNTA 3 - Convidados]
Texto: "Quantos convidados aproximadamente?"
Voz: "Legal! Quantas pessoas você está pensando em convidar? 
      Um número aproximado já ajuda bastante."

[PERGUNTA 4 - Cidade]
Texto: "Em qual cidade será?"
Voz: "Entendido! E em qual cidade será o evento?"

[PERGUNTA 5 - Orçamento]
Texto: "Qual sua faixa de investimento por pessoa?"
Voz: "Para eu te passar as melhores opções, qual é a faixa de 
      investimento que você está planejando por pessoa? 
      Pode ser algo como até 100 reais, de 100 a 200, 
      de 200 a 300, ou acima de 300."

---

=== SCORE ALTO (VOZ) ===
"Uau, que evento incrível! Pelo que você me contou, 
posso ver que vai ser algo especial. Vou conectar você 
com um dos nossos especialistas para apresentarmos 
as melhores opções. Pode me passar o melhor e-mail 
para enviarmos a agenda?"

=== SCORE MÉDIO (TEXTO) ===
"Entendido! Estou preparando algumas opções que 
podem se encaixar no seu evento. Posso te mandar 
aluns exemplos de eventos similares que fizemos?"

=== SCORE BAIXO (TEXTO) ===
"Agradeço seu contato! Vou guardar suas informações 
e assim que tivermos novidades que possam te interessar, 
entro em contato. Muito obrigado!"
```

---

## 📋 QUALIFICAÇÃO - CAMPOS OBRIGATÓRIOS

| Campo | Pergunta | Formato | Validação |
|-------|----------|---------|-----------|
| event_type | "Que tipo de evento?" | choice | casamento, aniversário, corporativo, congresso, formatura, outro |
| event_date | "Qual a data?" | date | >= today + 14 dias |
| guests_estimate | "Quantos convidados?" | number | 10-1000 |
| location_city | "Qual cidade?" | text | Lista de cidades atendidas |
| budget_per_person | "Investimento por pessoa?" | choice | <80, 80-150, 150-250, 250-400, >400 |

**Score por Campo:**

```javascript
const scoringRules = {
  event_type: {
    'casamento': 20,
    'formatura': 18,
    'corporativo': 17,
    'congresso': 15,
    'aniversario': 10,
    'outro': 5
  },
  
  budget_per_person: {
    '<80': 5,
    '80-150': 10,
    '150-250': 20,
    '250-400': 25,
    '>400': 30
  },
  
  guests_estimate: {
    '30-80': 10,
    '81-150': 15,
    '151-300': 20,
    '301-500': 25,
    '>500': 30
  },
  
  date_proximity: {
    '14-30 days': 5,
    '31-90 days': 15,
    '91-180 days': 20,
    '>180 days': 10
  }
}

function calculateScore(leadData) {
  let score = 0;
  score += scoringRules.event_type[leadData.event_type] || 0;
  score += scoringRules.budget_per_person[leadData.budget] || 0;
  // ... etc
  
  return Math.min(100, score);
}
```

---

## 📅 INTEGRAÇÃO GOOGLE CALENDAR

### Quando Agendar

```javascript
if (lead.score >= 70 && lead.qualified) {
  // Criar evento no Google Calendar
  const event = {
    summary: `Reunião Orkestra - ${lead.name}`,
    description: `
      Lead: ${lead.name}
      Evento: ${lead.event_type}
      Data: ${lead.event_date}
      Pessoas: ${lead.guests}
      Orçamento: ${lead.budget}
      
      Link qualificação: https://orkestra.ai/qual/${lead.id}
    `,
    start: {
      dateTime: suggestMeetingTime(),
      timeZone: 'America/Sao_Paulo'
    },
    end: {
      dateTime: suggestMeetingTime() + 30min,
      timeZone: 'America/Sao_Paulo'
    },
    attendees: [
      {email: lead.email},
      {email: assignAccountExecutive(lead)}
    ],
    conferenceData: {
      createRequest: {
        requestId: lead.id,
        conferenceSolutionKey: {type: 'hangoutsMeet'}
      }
    }
  };
}
```

### Mensagem de Confirmação

```
[VOZ]
"Perfeito, Maria! Já agendei uma conversa com nosso especialista 
para segunda-feira às 15 horas. Você vai receber um link do 
Google Meet no e-mail maria@email.com. É só clicar na hora 
marcada. Estamos ansiosos para conhecer melhor seu evento!"
```

---

## 📊 TABELAS DO SISTEMA

### 1. whatsapp_leads

| Campo | Tipo |
|-------|------|
| id | UUID PK |
| phone | TEXT (único) |
| name | TEXT |
| email | TEXT |
| source | TEXT (manychat, direct, campaign) |
| first_contact_at | TIMESTAMPTZ |
| last_contact_at | TIMESTAMPTZ |
| is_active | BOOLEAN |

### 2. whatsapp_conversations

| Campo | Tipo |
|-------|------|
| id | UUID PK |
| lead_id | UUID FK |
| session_id | TEXT |
| platform | TEXT (manychat, twilio) |
| status | ENUM (active, closed, paused) |
| current_stage | TEXT |
| turn_count | INTEGER |
| voice_preferred | BOOLEAN |

### 3. whatsapp_messages

| Campo | Tipo |
|-------|------|
| id | UUID PK |
| conversation_id | UUID FK |
| direction | ENUM (in, out) |
| content_type | ENUM (text, voice, image, document) |
| content_text | TEXT |
| voice_url | TEXT |
| voice_duration | NUMERIC |
| emotion_tag | TEXT |
| sent_at | TIMESTAMPTZ |

### 4. qualification_progress

| Campo | Tipo |
|-------|------|
| id | UUID PK |
| lead_id | UUID FK |
| field_name | TEXT |
| field_value | JSONB |
| is_filled | BOOLEAN |
| filled_at | TIMESTAMPTZ |

### 5. lead_voice_preferences

| Campo | Tipo |
|-------|------|
| lead_id | UUID FK |
| prefers_voice | BOOLEAN DEFAULT FALSE |
| detected_from_behavior | BOOLEAN |

---

## 🎯 REGRAS DE OURO

1. **Primeira mensagem SEMPRE em voz** — Cria conexão emocional
2. **Nunca demorar > 5 segundos** — Resposta imediata
3. **Alternar voz/texto** — Não saturar com áudio
4. **Fallback seguro** — Se voz falhar, texto imediato
5. **PT-BR nativo** — ElevenLabs com sotaque brasileiro
6. **Empatia > Eficiência** — Simular humano, não robot
7. **Nunca depender de humano** — 100% autônomo

---

🎛️ **SDR AI VOICE + WHATSAPP — Especificação Completa**
