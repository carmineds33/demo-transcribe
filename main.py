import streamlit as st
import boto3
import requests
import json
from botocore.exceptions import NoCredentialsError, EndpointConnectionError
from keysX import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION, BUCKET_NAME, INPUT_PATH

# Funzione per caricare i file su S3
def upload_file_to_s3(file):
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                      region_name=REGION)
    object_name = f"{INPUT_PATH}/{file.name}"

    try:
        s3.upload_fileobj(file, BUCKET_NAME, object_name)
        return True
    except FileNotFoundError:
        return False
    except NoCredentialsError:
        return False
    except EndpointConnectionError:
        return False

# Funzione per verificare lo stato della trascrizione
def check_transcription_job_status(job_name):
    transcribe_client = boto3.client('transcribe', region_name=REGION)
    try:
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        return response['TranscriptionJob']['TranscriptionJobStatus']  # 'COMPLETED', 'IN_PROGRESS', etc.
    except Exception as e:
        st.error(f"Errore nel verificare lo stato del lavoro di trascrizione: {str(e)}")
        return None

# Funzione per recuperare l'URL del risultato della trascrizione
def get_transcription_result_url(job_name):
    transcribe_client = boto3.client('transcribe', region_name=REGION)
    try:
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        if response['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            return response['TranscriptionJob']['Transcript']['TranscriptFileUri']
    except Exception as e:
        st.error(f"Errore nel recuperare l'URL del risultato della trascrizione: {str(e)}")
        return None

# Funzione per scaricare e visualizzare il JSON
def display_json(url):
    response = requests.get(url)
    if response.status_code == 200:
        json_data = response.json()
        st.expander("Visualizza JSON della Trascrizione", expanded=False).json(json_data)
    else:
        st.error("Errore nel scaricare il JSON della trascrizione.")

# Interfaccia grafica
st.title('Carica audio e trascrivi')

uploaded_file = st.file_uploader("Scegli un file audio", type=['mp3', 'wav'])
if uploaded_file is not None:
    # Assumiamo che `upload_file_to_s3` ritorni anche il job_name univoco per questo file
    if upload_file_to_s3(uploaded_file):
        st.success('File caricato con successo!')
        job_name = uploaded_file.name.replace(' ', '-').replace('.', '-')
        job_name = ''.join(c for c in job_name if c.isalnum() or c in ['.', '_', '-'])

        if st.button('Verifica Stato Trascrizione'):
            status = check_transcription_job_status(job_name)
            if status == 'COMPLETED':
                st.success('La trascrizione è completata.')
                result_url = get_transcription_result_url(job_name)
                if result_url:
                    st.markdown(f"Scarica il risultato della trascrizione [qui]({result_url})", unsafe_allow_html=True)
                    display_json(result_url)  # Chiama la funzione per visualizzare il JSON
            elif status == 'IN_PROGRESS':
                st.info('La trascrizione è ancora in corso. Riprova più tardi.')
            else:
                st.error('Errore o stato sconosciuto della trascrizione. Controlla il job manualmente.')
    else:
        st.error('Errore nel caricamento del file. Controlla le credenziali AWS e i permessi del bucket S3.')
