import streamlit as st
from faster_whisper import WhisperModel
from pathlib import Path
from docx import Document
from docx.shared import Pt
import tempfile
import os
import io
import time


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Transcritor de Reuniões",
    page_icon="🎙️",
    layout="wide"
)

st.title("🎙️ Transcritor de Reuniões")
st.caption(
    "Transcrição de áudio usando Faster-Whisper • "
    "Português • timestamps • TXT • SRT • Word"
)


# ============================================================
# FUNÇÕES
# ============================================================

def formatar_tempo(segundos):
    if segundos is None:
        segundos = 0

    segundos = int(segundos)

    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos = segundos % 60

    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def formatar_srt(segundos):
    if segundos is None:
        segundos = 0

    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    seg = int(segundos % 60)

    milissegundos = int(
        (segundos - int(segundos)) * 1000
    )

    return (
        f"{horas:02d}:"
        f"{minutos:02d}:"
        f"{seg:02d},"
        f"{milissegundos:03d}"
    )


@st.cache_resource
def carregar_modelo(nome_modelo, device, compute_type):

    return WhisperModel(
        nome_modelo,
        device=device,
        compute_type=compute_type
    )


def criar_word(nome_audio, segmentos):

    doc = Document()

    # Título
    titulo = doc.add_heading(
        "Transcrição da Reunião",
        level=0
    )

    doc.add_paragraph(
        f"Arquivo original: {nome_audio}"
    )

    doc.add_paragraph(
        "Transcrição automática realizada com Faster-Whisper."
    )

    doc.add_paragraph("")

    # Transcrição
    doc.add_heading(
        "Transcrição",
        level=1
    )

    for seg in segmentos:

        inicio = formatar_tempo(seg["start"])
        fim = formatar_tempo(seg["end"])

        p = doc.add_paragraph()

        tempo = p.add_run(
            f"[{inicio} – {fim}] "
        )

        tempo.bold = True

        texto = p.add_run(
            seg["text"]
        )

        texto.font.size = Pt(11)

    # Espaço para resumo posterior
    doc.add_page_break()

    doc.add_heading(
        "Resumo da Reunião",
        level=1
    )

    doc.add_paragraph(
        "Esta seção poderá ser preenchida após a revisão "
        "da transcrição."
    )

    doc.add_heading(
        "Decisões e Deliberações",
        level=2
    )

    doc.add_paragraph("")

    doc.add_heading(
        "Encaminhamentos",
        level=2
    )

    doc.add_paragraph("")

    doc.add_heading(
        "Responsáveis",
        level=2
    )

    doc.add_paragraph("")

    doc.add_heading(
        "Prazos",
        level=2
    )

    doc.add_paragraph("")

    doc.add_heading(
        "Pendências",
        level=2
    )

    doc.add_paragraph("")

    buffer = io.BytesIO()

    doc.save(buffer)

    buffer.seek(0)

    return buffer


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("⚙️ Configurações")


modelo = st.sidebar.selectbox(
    "Modelo Whisper",
    [
        "tiny",
        "base",
        "small",
        "medium",
        "large-v3"
    ],
    index=2
)


st.sidebar.markdown(
    """
**Sugestão**

- `tiny`: teste rápido
- `base`: rápido
- `small`: boa relação qualidade/velocidade
- `medium`: melhor qualidade
- `large-v3`: maior precisão, mas muito pesado
"""
)


idioma = st.sidebar.selectbox(
    "Idioma",
    [
        "Português",
        "Detecção automática"
    ]
)


beam_size = st.sidebar.slider(
    "Beam size",
    min_value=1,
    max_value=10,
    value=5
)


usar_vad = st.sidebar.checkbox(
    "Remover períodos de silêncio (VAD)",
    value=True
)


st.sidebar.divider()


st.sidebar.subheader("Processamento")


modo = st.sidebar.radio(
    "Dispositivo",
    [
        "CPU",
        "GPU NVIDIA"
    ]
)


if modo == "CPU":

    device = "cpu"
    compute_type = "int8"

else:

    device = "cuda"
    compute_type = "float16"


# ============================================================
# UPLOAD
# ============================================================

arquivo = st.file_uploader(
    "Selecione o áudio da reunião",
    type=[
        "m4a",
        "mp3",
        "wav",
        "ogg",
        "flac",
        "mp4",
        "webm"
    ]
)


if arquivo is not None:

    st.success(
        f"Arquivo carregado: {arquivo.name}"
    )

    tamanho_mb = (
        arquivo.size /
        1024 /
        1024
    )

    st.write(
        f"**Tamanho:** {tamanho_mb:.1f} MB"
    )

    st.audio(
        arquivo
    )


# ============================================================
# TRANSCRIÇÃO
# ============================================================

if arquivo is not None:

    if st.button(
        "🎙️ Iniciar transcrição",
        type="primary",
        use_container_width=True
    ):

        extensao = Path(
            arquivo.name
        ).suffix

        arquivo_temp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extensao
        )

        arquivo_temp.write(
            arquivo.getbuffer()
        )

        caminho_audio = (
            arquivo_temp.name
        )

        arquivo_temp.close()

        try:

            # =================================================
            # CARREGAR MODELO
            # =================================================

            with st.spinner(
                f"Carregando Whisper {modelo}..."
            ):

                model = carregar_modelo(
                    modelo,
                    device,
                    compute_type
                )

            st.success(
                "Modelo carregado."
            )


            # =================================================
            # PREPARAR INTERFACE
            # =================================================

            barra = st.progress(0)

            status = st.empty()

            contador = st.empty()

            transcricao_box = st.empty()


            status.info(
                "Analisando o áudio..."
            )


            # =================================================
            # IDIOMA
            # =================================================

            if idioma == "Português":

                language = "pt"

            else:

                language = None


            # =================================================
            # TRANSCRIÇÃO
            # =================================================

            inicio_processamento = time.time()


            segments, info = model.transcribe(

                caminho_audio,

                language=language,

                beam_size=beam_size,

                vad_filter=usar_vad,

                condition_on_previous_text=True,

                word_timestamps=False
            )


            duracao_audio = info.duration


            segmentos_salvos = []

            texto_interface = ""


            # =================================================
            # PROCESSAMENTO PROGRESSIVO
            # =================================================

            for numero, segment in enumerate(
                segments,
                start=1
            ):

                texto = (
                    segment.text.strip()
                )

                if not texto:

                    continue


                item = {

                    "start":
                        segment.start,

                    "end":
                        segment.end,

                    "text":
                        texto
                }


                segmentos_salvos.append(
                    item
                )


                inicio_txt = formatar_tempo(
                    segment.start
                )

                fim_txt = formatar_tempo(
                    segment.end
                )


                linha = (
                    f"[{inicio_txt} - "
                    f"{fim_txt}] "
                    f"{texto}\n"
                )


                texto_interface += linha


                # Progresso aproximado
                if duracao_audio > 0:

                    progresso = (
                        segment.end /
                        duracao_audio
                    )

                    progresso = min(
                        progresso,
                        1.0
                    )

                    barra.progress(
                        progresso
                    )


                status.info(
                    f"Transcrevendo: "
                    f"{inicio_txt} / "
                    f"{formatar_tempo(duracao_audio)}"
                )


                contador.caption(
                    f"{numero} segmentos processados"
                )


                transcricao_box.text_area(
                    "Transcrição em andamento",
                    texto_interface,
                    height=400
                )


            # =================================================
            # FINALIZAÇÃO
            # =================================================

            barra.progress(1.0)


            tempo_total = (
                time.time() -
                inicio_processamento
            )


            status.success(
                "Transcrição concluída!"
            )


            st.session_state[
                "segmentos"
            ] = segmentos_salvos


            st.session_state[
                "nome_audio"
            ] = arquivo.name


            st.session_state[
                "texto"
            ] = texto_interface


            # =================================================
            # INFORMAÇÕES
            # =================================================

            col1, col2, col3 = st.columns(3)


            col1.metric(
                "Duração do áudio",
                formatar_tempo(
                    duracao_audio
                )
            )


            col2.metric(
                "Segmentos",
                len(segmentos_salvos)
            )


            col3.metric(
                "Tempo de processamento",
                formatar_tempo(
                    tempo_total
                )
            )


        except Exception as erro:

            st.error(
                f"Erro durante a transcrição:\n\n{erro}"
            )


        finally:

            if os.path.exists(
                caminho_audio
            ):

                os.remove(
                    caminho_audio
                )


# ============================================================
# RESULTADOS
# ============================================================

if "segmentos" in st.session_state:

    st.divider()

    st.header(
        "📝 Resultado"
    )


    segmentos = (
        st.session_state[
            "segmentos"
        ]
    )


    texto = (
        st.session_state[
            "texto"
        ]
    )


    nome_audio = (
        st.session_state[
            "nome_audio"
        ]
    )


    st.text_area(
        "Transcrição completa",
        texto,
        height=500
    )


    # ========================================================
    # TXT
    # ========================================================

    txt_bytes = texto.encode(
        "utf-8"
    )


    # ========================================================
    # SRT
    # ========================================================

    srt = ""


    for i, seg in enumerate(
        segmentos,
        start=1
    ):

        srt += (
            f"{i}\n"
        )

        srt += (
            f"{formatar_srt(seg['start'])} --> "
            f"{formatar_srt(seg['end'])}\n"
        )

        srt += (
            f"{seg['text']}\n\n"
        )


    # ========================================================
    # WORD
    # ========================================================

    word_buffer = criar_word(
        nome_audio,
        segmentos
    )


    # ========================================================
    # BOTÕES
    # ========================================================

    st.subheader(
        "💾 Downloads"
    )


    col1, col2, col3 = st.columns(3)


    with col1:

        st.download_button(

            "📄 Baixar TXT",

            data=txt_bytes,

            file_name=(
                Path(nome_audio).stem +
                "_transcricao.txt"
            ),

            mime="text/plain",

            use_container_width=True
        )


    with col2:

        st.download_button(

            "🎬 Baixar SRT",

            data=srt.encode("utf-8"),

            file_name=(
                Path(nome_audio).stem +
                "_transcricao.srt"
            ),

            mime="text/plain",

            use_container_width=True
        )


    with col3:

        st.download_button(

            "📘 Baixar Word",

            data=word_buffer,

            file_name=(
                Path(nome_audio).stem +
                "_transcricao.docx"
            ),

            mime=(
                "application/"
                "vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),

            use_container_width=True
        )


    st.info(
        "Depois de gerar a transcrição, você pode "
        "me enviar o arquivo TXT ou Word. "
        "Eu posso revisar o texto e preparar a ata "
        "e o resumo da reunião."
    )
