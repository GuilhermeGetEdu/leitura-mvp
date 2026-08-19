import streamlit as st
import speech_recognition as sr
import jiwer
from audio_recorder_streamlit import audio_recorder
import io
import requests

st.set_page_config(page_title="Leitura MVP", page_icon="🎙️", layout="centered")
st.title("🎙️ Motor de Avaliação de Leitura (MVP)")

# URL do seu Webhook da Planilha (verifique se este é o seu link ativo do Apps Script)
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbx_SEU_WEBHOOK_AQUI/exec"

# Mapeamento fixo dos textos presentes na pasta do Google Drive
ARQUIVOS_DRIVE = {
    "Minha Casa": "https://docs.google.com/document/d/177yW8EjrHvlIEc3kQBuulYCxb6bpcquc7t8DbNVZY4/edit",
    "https://docs.google.com/document/d/1rzo5imfn3IzQ_dkIDOQi2ScEATn1aPIKd6usnrk6rOw/edit"
}

# Formulário Inicial
user_email = st.text_input("E-mail do Avaliador / Usuário Google:", "guilherme@getedu.com.br")
idade = st.text_input("Idade do Estudante:", "12")
serie = st.text_input("Série do Estudante:", "7")

st.write("---")
st.subheader("📚 Seleção do Texto de Leitura")

# Combo Box (Selectbox) para escolha do texto
opcao_selecionada = st.selectbox(
    "Escolha o texto da pasta para leitura:",
    options=list(ARQUIVOS_DRIVE.keys())
)

doc_link = ARQUIVOS_DRIVE[opcao_selecionada]
texto_original = ""

if doc_link:
    try:
        if "/d/" in doc_link:
            doc_id = doc_link.split("/d/")[1].split("/")[0]
        else:
            doc_id = doc_link.strip()
            
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        resp = requests.get(export_url)
        if resp.status_code == 200:
            texto_original = resp.text.strip()
            st.success(f"Texto '{opcao_selecionada}' carregado com sucesso!")
        else:
            st.error("Certifique-se de que o Google Doc individual está compartilhado como 'Qualquer pessoa com o link pode ver'.")
    except Exception as e:
        st.error("Erro ao carregar o texto.")

# Botão para abrir o Modal de Leitura
if texto_original and st.button("📖 Abrir Tela de Leitura"):
    st.session_state["abrir_modal"] = True

# MODAL DE LEITURA
@st.dialog("📖 Leitura do Aluno")
def modal_leitura():
    st.write("Instruções: Peça ao aluno para ler o texto em voz alta e clique no microfone para gravar.")
    
    col_texto, col_gravador = st.columns([2, 1])
    
    with col_texto:
        st.markdown(
            f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #1a73e8; font-size: 18px; line-height: 1.6;">
                {texto_original}
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    with col_gravador:
        st.write("### 🎙️ Gravador")
        audio_bytes = audio_recorder(text="Clique para gravar / parar", pause_threshold=2.0)
        
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            
            with st.spinner("Analisando fluência..."):
                r = sr.Recognizer()
                audio_file = io.BytesIO(audio_bytes)
                with sr.AudioFile(audio_file) as source:
                    audio_data = r.record(source)
                    duracao_segundos = len(audio_data.frame_data) / (audio_data.sample_rate * audio_data.sample_width)
                    
                try:
                    texto_lido = r.recognize_google(audio_data, language="pt-BR").lower()
                    
                    wpm = round(len(texto_lido.split()) / (duracao_segundos / 60)) if duracao_segundos > 0 else 0
                    
                    transformation = jiwer.Compose([jiwer.RemovePunctuation(), jiwer.ToLowerCase()])
                    orig_clean = transformation(texto_original)
                    lido_clean = transformation(texto_lido)
                    
                    wer = jiwer.wer(orig_clean, lido_clean)
                    accuracy = round(max(0, (1 - wer)) * 100)
                    
                    set_orig = set(orig_clean.split())
                    set_lido = set(lido_clean.split())
                    struggled = list(set_orig - set_lido)
                    str_struggled = ", ".join(struggled) if struggled else "Nenhuma!"
                    
                    st.success("Análise Concluída!")
                    st.metric("Precisão", f"{accuracy}%")
                    st.metric("WPM", wpm)
                    st.metric("Tempo", f"{round(duracao_segundos)}s")
                    
                    payload = {
                        "email": user_email,
                        "idade": idade,
                        "serie": serie,
                        "wpm": wpm,
                        "accuracy": accuracy,
                        "tempo": round(duracao_segundos),
                        "dificuldades": str_struggled,
                        "link_doc": doc_link
                    }
                    
                    try:
                        requests.post(WEBHOOK_URL, json=payload)
                        st.info("📊 Dados gravados na Coluna I da planilha!")
                    except:
                        pass
                        
                except sr.UnknownValueError:
                    st.error("Não foi possível reconhecer o áudio. Tente novamente.")

if st.session_state.get("abrir_modal", False):
    modal_leitura()
