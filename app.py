from flask import Flask, render_template, url_for, flash, redirect, request, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from config import Config
from nlp_utils import summarize_text, nlp_pipeline
from models import db, User, Summary
import os
import base64


app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.template_filter('b64encode')
def b64encode_filter(audio_content):
    return base64.b64encode(audio_content).decode('utf-8')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=request.form.get('remember'))
            flash('You have been logged in!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/")
@app.route("/home")
@login_required
def home():
    language_options = [
        {"id": 1, "name": "ENGLISH"},
        {"id": 2, "name": "HINDI"},
        {"id": 3, "name": "KANNADA"},
        {"id": 4, "name": "TAMIL"},
        {"id": 5, "name": "MALAYALAM"},
        {"id": 6, "name": "TELUGU"},
        {"id": 7, "name": "GUJARATI"},
        {"id": 8, "name": "MARATHI"},
        {"id": 9, "name": "BENGALI"},
        {"id": 10, "name": "PUNJABI"},
        {"id": 11, "name": "FRENCH"},
        {"id": 12, "name": "GERMAN"},
        {"id": 13, "name": "ITALIAN"},
        {"id": 14, "name": "JAPANESE"},
        {"id": 15, "name": "PORTUGUESE"},
        {"id": 16, "name": "RUSSIAN"},
        {"id": 17, "name": "SPANISH"},
    ]
    summaries = Summary.query.filter_by(user_id=current_user.id).all()
    return render_template('home.html', summaries=summaries, language_options=language_options)

@app.route("/summary", methods=['POST'])
@login_required
def summary():
    text = request.form['text']
    target_lang_id = int(request.form['language'])
    target_lang = {1: "en", 2: "hi", 3: "kn", 4: "ta", 5: "ml", 6: "te", 7: "gu", 8: "mr", 9: "bn", 10: "pa", 11: "fr", 12: "de", 13: "it", 14: "ja", 15: "pt", 16: "ru", 17: "es"}[target_lang_id]
    language_code = f"{target_lang}-{target_lang.upper()}"
    voice_name = {
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
        "pt": "pt-BR-Wavenet-A",
        "ru": "ru-RU-Wavenet-A",
        "es": "es-ES-Neural2-A"
    }[target_lang]

    summary_text = summarize_text(text)
    translated_text, audio_content = nlp_pipeline(summary_text, target_lang, language_code, voice_name, save_audio=True)

    # Save the summary and audio to the database
    summary = Summary(user_id=current_user.id, original_text=text, summary_text=summary_text, translated_text=translated_text, audio_content=audio_content)
    db.session.add(summary)
    db.session.commit()

    flash('Summary and audio have been generated!', 'success')
    return redirect(url_for('home'))

@app.route('/previous_summaries', methods=['GET'])
@login_required
def previous_summaries():
    summaries = Summary.query.filter_by(user_id=current_user.id).all()
    return render_template('previous_summaries.html', summaries=summaries)

if __name__ == '__main__':
    app.run(debug=True)
