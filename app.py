import os
import time
import tempfile
import importlib

st = importlib.import_module("streamlit")
from google import genai

# ----------------------------------------------------------------------------
# Translations — every UI string lives here, keyed by language
# ----------------------------------------------------------------------------
TEXT = {
    "en": {
        "page_title": "AI Football Tactical Analyzer",
        "title": "⚽ AI Post-Play Tactical Analyzer",
        "caption": "Upload a 15-second clip to generate an instant tactical report evaluated against your game model.",
        "config_header": "⚙️ Configuration",
        "game_model_header": "📋 Game Model Principles",
        "select_philosophy": "Select the Tactical Philosophy:",
        "custom_rules_label": "Specific instructions or rules:",
        "custom_rules_placeholder": "E.g.: Wingers must cut inside; the pivot drops between the center-backs.",
        "team_color_label": "Team to Analyze (Shirt Color):",
        "team_color_default": "Blue / White",
        "missing_key_error": "⚠️ App is missing its Gemini API key. (Site owner: add GEMINI_API_KEY to your Streamlit secrets.)",
        "model_caption": "🤖 Powered by Gemini 3.5 Flash-Lite (with automatic fallback if overloaded)",
        "uploader_label": "Upload the play clip (MP4, MOV — max. 15-20 sec)",
        "video_header": "📹 Play Video",
        "report_header": "📊 Tactical Report",
        "analyze_button": "🚀 Analyze Play",
        "no_key_error": "The app isn't configured with an API key yet — please try again later.",
        "spinner_text": "Analyzing spacing, pitch occupation, and game-model compliance...",
        "success_message": "Analysis completed successfully!",
        "processing_error": "Error while processing the video: {error}",
    },
    "es": {
        "page_title": "Analizador Táctico de Fútbol con IA",
        "title": "⚽ Analizador Táctico Post-Jugada con IA",
        "caption": "Sube un clip de 15 segundos para generar un reporte táctico instantáneo contrastado con el modelo de juego.",
        "config_header": "⚙️ Configuración",
        "game_model_header": "📋 Principios del Modelo de Juego",
        "select_philosophy": "Selecciona la Filosofía Táctica:",
        "custom_rules_label": "Instrucciones o reglas específicas:",
        "custom_rules_placeholder": "Ej: Los extremos deben cerrar por dentro; el pivote se incrusta entre centrales.",
        "team_color_label": "Equipo a Analizar (Color de Camiseta):",
        "team_color_default": "Azul / Blanco",
        "missing_key_error": "⚠️ A la app le falta la clave de API de Gemini. (Dueño del sitio: agrega GEMINI_API_KEY en los Secrets de Streamlit.)",
        "model_caption": "🤖 Impulsado por Gemini 3.5 Flash-Lite (con respaldo automático si está saturado)",
        "uploader_label": "Cargar clip de la jugada (MP4, MOV — máx. 15-20 seg)",
        "video_header": "📹 Video de la Jugada",
        "report_header": "📊 Reporte Táctico",
        "analyze_button": "🚀 Analizar Jugada",
        "no_key_error": "La app aún no tiene configurada su clave de API — por favor intenta más tarde.",
        "spinner_text": "Analizando espacios, ocupación del campo y cumplimiento del modelo de juego...",
        "success_message": "¡Análisis completado con éxito!",
        "processing_error": "Error durante el procesamiento del video: {error}",
    },
}

# Tactical model descriptions, keyed by a stable id so switching language
# never loses track of which philosophy is selected.
GAME_MODELS = {
    "positional": {
        "en": "Positional Play: Short passing, fix-and-split, width via wingers, passes between the lines and third-man combinations.",
        "es": "Juego de Posición: Pases cortos, fijar y dividir, amplitud con extremos, pases entre líneas y tercer hombre.",
    },
    "gegenpressing": {
        "en": "High Press After Loss (Gegenpressing): Immediate pressure within 5 seconds, high block, space compression.",
        "es": "Presión Alta Tras Pérdida (Gegenpressing): Acoso inmediato antes de 5 segundos, bloque alto, reducción de espacios.",
    },
    "counter": {
        "en": "Fast Transition / Counter-Attack: Immediate verticality after regaining possession, mid-to-low block, attacks into space.",
        "es": "Transición Rápida / Contraataque: Verticalidad inmediata tras recuperación, bloque medio-bajo, ataques al espacio.",
    },
    "custom": {
        "en": "Custom Tactical Model",
        "es": "Modelo Táctico Personalizado",
    },
}
MODEL_ORDER = ["positional", "gegenpressing", "counter", "custom"]

PROMPT_TEMPLATES = {
    "en": """
    You are an elite professional football performance and tactics analyst.
    Analyze the attached 15-second video clip in detail, focusing exclusively on the team you see wearing: {team_color}.

    The Game Model and guidelines established for this team are:
    {game_model_text} {custom_rules}

    Generate a concise, rigorous post-play report in ENGLISH, structured exactly with the following Markdown format:

    ### 1. 🟢 Positive Tactical Aspects
    - Identify 2 or 3 standout actions (e.g.: good defensive shifting, marking/tracking runners, supporting/breaking movements, or speed of circulation).

    ### 2. 📊 Key Actions & Observed Events
    - Passes attempted / completed during the sequence.
    - Intensity of the opposing or own team's press (High / Medium / Low).
    - Players or positions decisive to how the action developed.

    ### 3. ⚠️ Alignment with the Game Model & Improvement Opportunities
    - Point out technical or tactical errors relative to the established game model (e.g.: lack of width, losses of possession in dangerous zones, slow recovery shape).
    - Provide 1 corrective, actionable recommendation for the coaching staff to work on with the squad.
    """,
    "es": """
    Eres un analista de rendimiento y táctica de fútbol profesional de élite.
    Analiza detalladamente el clip de video adjunto de 15 segundos enfocándote exclusivamente en el equipo que viste: {team_color}.

    El Modelo de Juego y directrices establecidas para este equipo son:
    {game_model_text} {custom_rules}

    Genera un reporte post-jugada conciso, riguroso y en ESPAÑOL, estructurado exactamente con el siguiente formato Markdown:

    ### 1. 🟢 Aspectos Tácticos Positivos
    - Identifica 2 o 3 acciones destacadas (ej: buena basculación, fijación de marcas, desmarques de apoyo/ruptura o velocidad de circulación).

    ### 2. 📊 Acciones Clave y Eventos Observados
    - Pases intentados / completados en la secuencia.
    - Intensidad de la presión rival o propia (Alta / Media / Baja).
    - Jugadores o posiciones determinantes en el desarrollo de la acción.

    ### 3. ⚠️ Alineación con el Modelo de Juego y Oportunidades de Mejora
    - Señala errores técnicos o tácticos respecto al modelo de juego establecido (ej: falta de amplitud, pérdidas en zonas de seguridad, lentitud en el repliegue).
    - Entrega 1 recomendación correctiva y accionable para que el cuerpo técnico la trabaje con la plantilla.
    """,
}


def generate_with_fallback(client, video_file, prompt, models, max_retries_per_model=2):
    """Try each model in order; on a 503 (overloaded) error, back off briefly and
    retry, then move on to the next model. Any other kind of error is raised
    immediately instead of being retried."""
    last_error = None
    for model_name in models:
        for attempt in range(max_retries_per_model):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[video_file, prompt],
                )
                return response, model_name
            except Exception as e:
                last_error = e
                if "503" in str(e) or "UNAVAILABLE" in str(e):
                    time.sleep(2 ** attempt)
                    continue
                raise
    raise last_error


# ----------------------------------------------------------------------------
# Language selector — placed first so it controls everything drawn after it
# ----------------------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "en"

st.set_page_config(page_title=TEXT[st.session_state.lang]["page_title"], page_icon="⚽", layout="wide")

with st.sidebar:
    lang_choice = st.radio(
        "🌐 Language / Idioma",
        options=["en", "es"],
        format_func=lambda code: "English" if code == "en" else "Español",
        horizontal=True,
        key="lang",
    )

t = TEXT[st.session_state.lang]  # shorthand for the active language's strings

st.title(t["title"])
st.caption(t["caption"])

# ----------------------------------------------------------------------------
# Sidebar: Configuration
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header(t["config_header"])

    st.subheader(t["game_model_header"])
    selected_model_id = st.selectbox(
        t["select_philosophy"],
        options=MODEL_ORDER,
        format_func=lambda mid: GAME_MODELS[mid][st.session_state.lang],
        key="game_model_id",
    )
    game_model_text = GAME_MODELS[selected_model_id][st.session_state.lang]

    custom_rules = ""
    if selected_model_id == "custom":
        custom_rules = st.text_area(
            t["custom_rules_label"],
            t["custom_rules_placeholder"],
            key="custom_rules",
        )

    team_color = st.text_input(
        t["team_color_label"],
        value=t["team_color_default"],
        key="team_color",
    )

    st.divider()

    # Load the Gemini API key from Streamlit secrets — never shown to or entered by the visitor
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        api_key = None
        st.error(t["missing_key_error"])

    # Preferred model, with fallbacks in case Google's capacity for one is temporarily overloaded (503)
    MODEL_FALLBACK_CHAIN = ["gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"]
    st.caption(t["model_caption"])

# ----------------------------------------------------------------------------
# Main section: Video upload
# ----------------------------------------------------------------------------
uploaded_file = st.file_uploader(t["uploader_label"], type=["mp4", "mov", "avi"])

if uploaded_file:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader(t["video_header"])
        st.video(uploaded_file)

    with col2:
        st.subheader(t["report_header"])
        if st.button(t["analyze_button"], type="primary"):
            if not api_key:
                st.error(t["no_key_error"])
            else:
                with st.spinner(t["spinner_text"]):
                    try:
                        # 1. Save the file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_file_path = tmp_file.name

                        # 2. Initialize client and upload file
                        client = genai.Client(api_key=api_key)
                        video_file = client.files.upload(file=tmp_file_path)

                        # 3. Structured tactical prompt — fully in whichever
                        # language is currently selected, instructions included
                        prompt = PROMPT_TEMPLATES[st.session_state.lang].format(
                            team_color=team_color,
                            game_model_text=game_model_text,
                            custom_rules=custom_rules,
                        )

                        # 4. Generate the report, falling back across models if overloaded
                        response, used_model = generate_with_fallback(
                            client, video_file, prompt, MODEL_FALLBACK_CHAIN
                        )

                        # 5. Render the result
                        st.success(t["success_message"])
                        st.markdown(response.text)

                        # Clean up the temporary file
                        os.remove(tmp_file_path)

                    except Exception as e:
                        st.error(t["processing_error"].format(error=str(e)))
