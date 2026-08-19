import streamlit as st
import speech_recognition as sr
import jiwer
from audio_recorder_streamlit import audio_recorder
import io
import requests

st.set_page_config(page_title="Leitura MVP", page_icon="🎙️")
st.title("🎙️ Motor de Avaliação de Leitura (MVP)")

# Formulário de entrada
user_email = st.text_input("E-mail do Avaliador / Usuário Google:")
idade = st.text_input("Idade do Estudante:")
serie = st.text_input("Série do Estudante:")
texto_original = st.text_area("Cole aqui o texto de referência para a leitura:")

st.write("---")
st.write("### 🔴 Grave a Leitura")
audio_bytes = audio_recorder(text="Clique no microfone, leia e clique novamente para parar", pause_threshold=2.0)

if audio_bytes and texto_original:
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner("A IA está analisando a fluência..."):
        r = sr.Recognizer()
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            duracao_segundos = len(audio_data.frame_data) / (audio_data.sample_rate * audio_data.sample_width)
            
        try:
            texto_lido = r.recognize_google(audio_data, language="pt-BR").lower()
            
            # Cálculo de WPM
            wpm = round(len(texto_lido.split()) / (duracao_segundos / 60)) if duracao_segundos > 0 else 0
            
            # Cálculo de Precisão
            transformation = jiwer.Compose([jiwer.RemovePunctuation(), jiwer.ToLowerCase()])
            orig_clean = transformation(texto_original)
            lido_clean = transformation(texto_lido)
            
            wer = jiwer.wer(orig_clean, lido_clean)
            accuracy = round(max(0, (1 - wer)) * 100)
            
            # Palavras com dificuldade
            set_orig = set(orig_clean.split())
            set_lido = set(lido_clean.split())
            struggled = list(set_orig - set_lido)
            str_struggled = ", ".join(struggled) if struggled else "Nenhuma!"
            
            st.success("Análise Concluída!")
            col1, col2, col3 = st.columns(3)
            col1.metric("Precisão", f"{accuracy}%")
            col2.metric("WPM", wpm)
            col3.metric("Tempo", f"{round(duracao_segundos)}s")
            
            st.write("**O que a IA escutou:**", texto_lido)
            st.write("**Dificuldades detectadas:**", str_struggled)
            
            # Salvar automaticamente na Planilha via Webhook
            WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwaBC2f1R10P3RSxJVoazh7nTKT2NzA4Goz-abmjml0S81g1wpYExry4ic_WhKfzI0d/exec" # Substituiremos no próximo passo
            
            payload = {
                "email": user_email,
                "idade": idade,
                "serie": serie,
                "wpm": wpm,
                "accuracy": accuracy,
                "tempo": round(duracao_segundos),
                "dificuldades": str_struggled
            }
            
            # Envio silencioso para a planilha
            try:
                requests.post(WEBHOOK_URL, json=payload)
                st.info("📊 Dados gravados na planilha oficial!")
            except:
                pass

        except sr.UnknownValueError:
            st.error("A IA não conseguiu reconhecer o áudio. Fale mais perto do microfone.")
