from transformers import PegasusForConditionalGeneration, PegasusTokenizer
import torch
from google.cloud import texttospeech
import os
from langdetect import detect
from deep_translator import GoogleTranslator
from datetime import datetime
import hashlib
import concurrent.futures

# Set the path for Google Cloud service account credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "basic-cabinet-425722-c0-011804de4ab6.json"

# Initialize the Google Cloud Text-to-Speech client
client = texttospeech.TextToSpeechClient()

# Initialize the Pegasus model and tokenizer
model_name = 'human-centered-summarization/financial-summarization-pegasus'
tokenizer = PegasusTokenizer.from_pretrained(model_name)
model = PegasusForConditionalGeneration.from_pretrained(model_name)

# Cache to store previously processed texts along with their translated text and corresponding audio content
cache = {}

# Language map
map_dct = {
    1: "en", 2: "hi", 3: "kn", 4: "ta", 5: "ml", 6: "te", 7: "gu", 8: "mr", 9: "bn", 10: "pa",
    11: "fr", 12: "de", 13: "it", 14: "ja", 15: "pt", 16: "ru", 17: "es"
}

# Voice map
voice_map = {
    "en": "en-US-Neural2-J",
    "hi": "hi-IN-Wavenet-A",
    "kn": "kn-IN-Wavenet-A",
    "ta": "ta-IN-Wavenet-A",
    "ml": "ml-IN-Wavenet-A",
    "te": "te-IN-Wavenet-A",
    "gu": "gu-IN-Wavenet-A",
    "mr": "mr-IN-Wavenet-A",
    "bn": "bn-IN-Wavenet-A",
    "pa": "pa-IN-Wavenet-A",
    "fr": "fr-FR-Neural2-A",
    "de": "de-DE-Neural2-A",
    "it": "it-IT-Neural2-A",
    "ja": "ja-JP-Neural2-A",
    "pt": "pt-BR-Neural2-A",
    "ru": "ru-RU-Wavenet-A",
    "es": "es-ES-Neural2-A"
}

def translate_text(text, target_lang):
    org_lang = detect(text)
    if org_lang != 'en':
        text = GoogleTranslator(source=org_lang, target='en').translate(text)
    translated_text = GoogleTranslator(source='en', target=target_lang).translate(text)
    return translated_text

def synthesize_text(text, language_code, voice_name):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content

def summarize_text(text):
    inputs = tokenizer(text, return_tensors='pt')
    if inputs['input_ids'].shape[1] > 512:
        def split_text(text, max_length):
            tokens = tokenizer.tokenize(text)
            chunks = [tokens[i:i + max_length] for i in range(0, len(tokens), max_length)]
            return chunks

        chunks = split_text(text, 512)

        # Process chunks in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            partial_summaries = list(executor.map(
                lambda chunk: tokenizer.decode(
                    model.generate(torch.tensor([tokenizer.convert_tokens_to_ids(chunk)]), min_length=50, max_length=200, num_beams=10, early_stopping=True)[0],
                    skip_special_tokens=True
                ), chunks
            ))

        combined_summary_text = ' '.join(partial_summaries)
        inputs = tokenizer(combined_summary_text, max_length=512, truncation=True, return_tensors='pt')
        final_summary_ids = model.generate(inputs['input_ids'],
                                           min_length=50, 
                                           max_length=200, 
                                           num_beams=10, 
                                           early_stopping=True)
        final_summary = tokenizer.decode(final_summary_ids[0], skip_special_tokens=True)
    else:
        inputs = tokenizer(text, max_length=512, truncation=True, return_tensors='pt')
        summary_ids = model.generate(inputs['input_ids'],
                                     min_length=50, 
                                     max_length=200, 
                                     num_beams=10, 
                                     early_stopping=True)
        final_summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

    return final_summary

def nlp_pipeline(text, target_lang, language_code, voice_name, save_audio=False):
    text_hash = hashlib.md5(text.encode()).hexdigest()
    
    if text_hash in cache:
        return cache[text_hash]["translated_text"], cache[text_hash]["audio_content"]
    
    translated_text = translate_text(text, target_lang)
    audio_content = synthesize_text(translated_text, language_code, voice_name)
    
    cache[text_hash] = {
        "translated_text": translated_text,
        "audio_content": audio_content
    }
    
    if save_audio:
        current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{target_lang}_output_{current_datetime}.mp3"
        output_path = os.path.join('static/audio', output_filename)
        with open(output_path, "wb") as out:
            out.write(audio_content)
    
    return translated_text, audio_content
