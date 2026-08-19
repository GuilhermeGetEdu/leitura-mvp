import streamlit as st
import speech_recognition as sr
import jiwer
from audio_recorder_streamlit import audio_recorder
import io
import requests

st.set_page_config(page_title="Leitura MVP", page_icon="🎙️", layout="wide")
st.title("🎙️ Motor de Avaliação de Leitura (MVP)")

# URL do Webhook da Planilha (Verifique se é o seu link ativo do Apps Script)
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbx_SEU_WEBHOOK_AQUI/exec"

# Mapeamento dos textos da pasta do Google Drive
ARQUIVOS_DRIVE = {
    "Minha Casa": "https://docs.google.com/document/d/177yW8EjrHvlIEc3kQBuulYCxb6bpcquc7t8DbNVZY4/edit",
    "A BONECA-BEBÊ": "https://docs.google.com/document/d/1rzo5imfn3IzQ_dkIDOQi2ScEATn1aPIKd6usnrk6r0w/edit"
}

# Cabeçalho: Dados do Aluno
col1, col2, col3 = st.columns(3)
with col1:
    user_email = st.text_input("E-mail do Avaliador:", "guilherme@getedu.com.br")
with col2:
    idade = st.text_input("Idade do Estudante:", "12")
with col3:
    serie = st.text_input("Série do Estudante:", "7")

# Seleção do Texto
opcao_selecionada = st.selectbox(
    "📚 Escolha o texto da pasta para a leitura:",
    options=list(ARQUIVOS_DRIVE.keys())
)

doc_link = ARQUIVOS_DRIVE[opcao_selecionada]
texto_original = ""

if doc_link:
    try:
        doc_id = doc_link.split("/d/")[1].split("/")[0] if "/d/" in doc_link else doc_link.strip()
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        resp = requests.get(export_url)
        if resp.status_code == 200:
            texto_original = resp.text.strip()
        else:
            st.error("Não foi possível baixar o texto. Verifique se o arquivo está compartilhado como 'Qualquer pessoa com o link'.")
    except Exception:
        st.error("Erro ao conectar com o Google Drive.")

st.write("---")

# Área de Leitura e Gravação Lado a Lado
if texto_original:
    col_texto, col_gravacao = st.columns([2, 1], gap="large")
    
    with col_texto:
        st.subheader(f"📖 Texto: {opcao_selecionada}")
        st.markdown(
            f"""
            <div style="background-color: #f0f4f9; padding: 25px; border-radius: 12px; border-left: 6px solid #1a73e8; font-size: 22px; line-height: 1.8; color: #1f1f1f;">
                {texto_original}
            </div>
            """, 
            unsafe_allow_html=True
        )

    with col_gravacao:
        st.subheader("🎙️ Gravação")
        st.caption("Peça ao aluno para ler o texto ao lado e clique no microfone:")
        
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
                        st.info("📊 Salvo na Coluna I da planilha!")
                    except:
                        pass
                        
                except sr.UnknownValueError:
                    st.error("Não foi possível reconhecer o áudio. Tente novamente.")
