import os
import tempfile
import streamlit as st
from google import genai

# Page configuration
st.set_page_config(page_title="AI Football Tactical Analyzer", page_icon="⚽", layout="wide")

st.title("⚽ AI Post-Play Tactical Analyzer")
st.caption("Upload a 15-second clip to generate an instant tactical report evaluated against your game model.")

# Sidebar: Configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("📋 Game Model Principles")
    game_model = st.selectbox(
        "Select the Tactical Philosophy:",
        [
            "Positional Play: Short passing, fix-and-split, width via wingers, passes between the lines and third-man combinations.",
            "High Press After Loss (Gegenpressing): Immediate pressure within 5 seconds, high block, space compression.",
            "Fast Transition / Counter-Attack: Immediate verticality after regaining possession, mid-to-low block, attacks into space.",
            "Custom Tactical Model"
        ]
    )

    custom_rules = ""
    if game_model == "Custom Tactical Model":
        custom_rules = st.text_area("Specific instructions or rules:", "E.g.: Wingers must cut inside; the pivot drops between the center-backs.")

    team_color = st.text_input("Team to Analyze (Shirt Color):", value="Blue / White")

    st.divider()

    # Load the Gemini API key from Streamlit secrets — never shown to or entered by the visitor
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        api_key = None
        st.error("⚠️ App is missing its Gemini API key. (Site owner: add GEMINI_API_KEY to your Streamlit secrets.)")

    # Dynamic model selector
    selected_model = None
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            valid_models = []
            for m in client.models.list():
                # Only keep models that support the generateContent action (video/text analysis)
                if "generateContent" in getattr(m, 'supported_actions', []):
                    valid_models.append(m.name.replace("models/", ""))

            if valid_models:
                valid_models.sort(reverse=True)
                st.subheader("🤖 AI Engine")
                selected_model = st.selectbox("Available model:", valid_models)
            else:
                st.warning("No valid model available for this key.")
        except Exception:
            st.error("Error validating the API Key or listing available models.")

# Main section: Video upload
uploaded_file = st.file_uploader("Upload the play clip (MP4, MOV — max. 15-20 sec)", type=["mp4", "mov", "avi"])

if uploaded_file:
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📹 Play Video")
        st.video(uploaded_file)

    with col2:
        st.subheader("📊 Tactical Report")
        if st.button("🚀 Analyze Play", type="primary"):
            if not api_key:
                st.error("The app isn't configured with an API key yet — please try again later.")
            else:
                with st.spinner("Analyzing spacing, pitch occupation, and game-model compliance..."):
                    try:
                        # 1. Save the file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_file_path = tmp_file.name

                        # 2. Initialize client and upload file
                        client = genai.Client(api_key=api_key)
                        video_file = client.files.upload(file=tmp_file_path)

                        # 3. Structured tactical prompt (English)
                        prompt = f"""
                        You are an elite professional football performance and tactics analyst.
                        Analyze the attached 15-second video clip in detail, focusing exclusively on the team you see wearing: {team_color}.

                        The Game Model and guidelines established for this team are:
                        {game_model} {custom_rules}

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
                        """

                        # 4. Generate the report
                        response = client.models.generate_content(
                            model=selected_model,
                            contents=[video_file, prompt],
                        )

                        # 5. Render the result
                        st.success("Analysis completed successfully!")
                        st.markdown(response.text)

                        # Clean up the temporary file
                        os.remove(tmp_file_path)

                    except Exception as e:
                        st.error(f"Error while processing the video: {str(e)}")