import os
import tempfile
import streamlit as st
from google import genai

# Configuración de página
st.set_page_config(page_title="Analizador Táctico IA de Fútbol", page_icon="⚽", layout="wide")

st.title("⚽ Analizador Táctico Post-Jugada con IA")
st.caption("Sube un clip de 15 segundos para generar un reporte táctico instantáneo contrastado con el modelo de juego.")

# Barra lateral: Configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("API Key de Google Gemini", type="password", help="Obtén tu clave gratuita en Google AI Studio")
    
    st.subheader("📋 Principios del Modelo de Juego")
    game_model = st.selectbox(
        "Selecciona la Filosofía Táctica:",
        [
            "Juego de Posición: Pases cortos, fijar y dividir, amplitud con extremos, pases entre líneas y tercer hombre.",
            "Presión Alta Tras Pérdida (Gegenpressing): Acoso inmediato antes de 5 segundos, bloque alto, reducción de espacios.",
            "Transición Rápida / Contraataque: Verticalidad inmediata tras recuperación, bloque medio-bajo, ataques al espacio.",
            "Modelo Táctico Personalizado"
        ]
    )
    
    custom_rules = ""
    if game_model == "Modelo Táctico Personalizado":
        custom_rules = st.text_area("Instrucciones o reglas específicas:", "Ej: Los extremos deben cerrar por dentro; el pivote se incrusta entre centrales.")
    
    team_color = st.text_input("Equipo a Analizar (Color de Camiseta):", value="Azul / Blanco")
    
    st.divider()
    
    # Selector dinámico de modelos
    selected_model = None
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            valid_models = []
            for m in client.models.list():
                # Filtra solo los modelos que soportan la acción de generar contenido (video/análisis de texto)
                if "generateContent" in getattr(m, 'supported_actions', []):
                    valid_models.append(m.name.replace("models/", ""))
                             
            if valid_models:
                valid_models.sort(reverse=True)
                st.subheader("🤖 Motor de IA")
                selected_model = st.selectbox("Modelo disponible:", valid_models)
            else:
                st.warning("No hay modelo válido disponible para ésta llave.")
        except Exception:
            st.error("Error al validar la API Key o listar modelos disponibles.")
                                    
        # Sección Principal: Carga de Video
uploaded_file = st.file_uploader("Cargar clip de la jugada (MP4, MOV - máx. 15-20 seg)", type=["mp4", "mov", "avi"])

if uploaded_file:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📹 Video de la Jugada")
        st.video(uploaded_file)
        
    with col2:
        st.subheader("📊 Reporte Táctico")
        
        if st.button("🚀 Analizar Jugada", type="primary"):
            if not api_key:
                st.error("Por favor ingresa tu API Key en la barra lateral.")
            else:
                with st.spinner("Analizando espacios, ocupación del campo y cumplimiento del modelo de juego..."):
                    try:
                        # 1. Guardar archivo temporalmente
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_file_path = tmp_file.name

                        # 2. Inicializar cliente y subir archivo
                        client = genai.Client(api_key=api_key)
                        video_file = client.files.upload(file=tmp_file_path)

                        # 3. Prompt táctico en español estructurado
                        prompt = f"""
                        Eres un analista de rendimiento y táctica de fútbol profesional de élite.
                        Analiza detalladamente el clip de video adjunto de 15 segundos enfocándote exclusivamente en el equipo que viste: {team_color}.
                        
                        El Modelo de Juego y directrices establecidas para este equipo son:
                        {game_model} {custom_rules}
                        
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
                        """

                        # 4. Generación del reporte
                        response = client.models.generate_content(
                            model=selected_model,
                            contents=[video_file, prompt],
                        )

                        # 5. Renderizado del resultado
                        st.success("¡Análisis completado con éxito!")
                        st.markdown(response.text)

                        # Limpieza del archivo temporal
                        os.remove(tmp_file_path)

                    except Exception as e:
                        st.error(f"Error durante el procesamiento del video: {str(e)}")