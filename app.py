#app.py
import os
from flask import Flask, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
from html2image import Html2Image
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/generated', exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_age(age_str):
    try:
        age = int(age_str)
        if age < 16:
            return False, "Fighter must be at least 16 years old for safety compliance"
        elif age > 65:
            return False, "Maximum age limit is 65 years for safety compliance"
        elif age < 18:
            return True, f"Minor fighter (age {age}) - requires parental consent and additional safety protocols"
        else:
            return True, None
    except (ValueError, TypeError):
        return False, "Please enter a valid age (numbers only)"

def validate_weight_class(weight_class):
    valid_classes = [
        'Strawweight', 'Flyweight', 'Bantamweight', 'Featherweight', 
        'Lightweight', 'Welterweight', 'Middleweight', 'Light Heavyweight', 
        'Heavyweight', 'Super Heavyweight'
    ]
    if weight_class.title() not in valid_classes:
        return False, f"Please select a valid weight class: {', '.join(valid_classes)}"
    return True, None

def validate_record(wins, losses):
    try:
        wins = int(wins)
        losses = int(losses)
        if wins < 0 or losses < 0:
            return False, "Wins and losses cannot be negative"
        if wins + losses > 100:
            return False, "Total fights cannot exceed 100 (please verify record)"
        return True, None
    except (ValueError, TypeError):
        return False, "Please enter valid numbers for wins and losses"

def sanitize_input(text):
    if not text:
        return ""
    text = re.sub(r'[<>"\']', '', text)
    return text[:500].strip()

def render_card_to_png(fighter_data, template_name='card_default.html', output_file='output_card.png'):
    try:
        rendered_html = render_template(template_name, fighter=fighter_data)
        temp_file = 'temp_card_rendered.html'
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
        hti = Html2Image(output_path='static/generated/')
        hti.screenshot(html_file=temp_file, save_as=output_file, size=(1080, 1920))
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return True, None
    except Exception as e:
        return False, f"Error generating card image: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/card', methods=['POST'])
def card():
    try:
        card_style = request.form.get('card_style', 'default')
        template_name = f'card_{card_style}.html'
        name = sanitize_input(request.form.get('name', ''))
        age_str = request.form.get('age', '')
        weight_class = sanitize_input(request.form.get('weight_class', ''))
        wins_str = request.form.get('wins', '0')
        losses_str = request.form.get('losses', '0')
        draws_str = request.form.get('draws', '0')
        bio = sanitize_input(request.form.get('bio', ''))
        height = sanitize_input(request.form.get('height', ''))
        weight = sanitize_input(request.form.get('weight', ''))
        reach = sanitize_input(request.form.get('reach', ''))
        style = sanitize_input(request.form.get('style', ''))
        if style == 'Other':
            style = sanitize_input(request.form.get('custom_style', 'Other')),
        fight_name = sanitize_input(request.form.get('fight_name', ''))
        fights_out_of = sanitize_input(request.form.get('fights_out_of', ''))


        errors = []
        warnings = []

        if not name or len(name) < 2:
            errors.append("Fighter name must be at least 2 characters long")

        age_valid, age_message = validate_age(age_str)
        if not age_valid:
            errors.append(age_message)
        else:
            age = int(age_str)
            if age_message:
                warnings.append(age_message)

        weight_valid, weight_message = validate_weight_class(weight_class)
        if not weight_valid:
            errors.append(weight_message)

        record_valid, record_message = validate_record(wins_str, losses_str)
        if not record_valid:
            errors.append(record_message)
        else:
            wins = int(wins_str)
            losses = int(losses_str)
            draws = int(draws_str) if draws_str.isdigit() else 0

        if not bio or len(bio) < 10:
            errors.append("Bio must be at least 10 characters long")

        image = request.files.get('image')
        image_path = None
        if image and image.filename:
            if not allowed_file(image.filename):
                errors.append("Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WEBP files only")
            else:
                filename = secure_filename(image.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
                filename = timestamp + filename
                image_path = f'uploads/{filename}'
                try:
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                except Exception as e:
                    errors.append(f"Error saving image: {str(e)}")

        if errors:
            for error in errors:
                flash(error, 'error')
            for warning in warnings:
                flash(warning, 'warning')
            return redirect(url_for('index'))

        for warning in warnings:
            flash(warning, 'warning')

        fighter_data = {
            'name': name,
            'age': age,
            'weight_class': weight_class.title(),
            'wins': wins,
            'losses': losses,
            'bio': bio,
            'image': image_path,
            'total_fights': wins + losses + draws,
            'win_percentage': round((wins / (wins + losses + draws) * 100), 1) if (wins + losses + draws) > 0 else 0,
            'created_date': datetime.now().strftime("%B %d, %Y"),
            'fight_name': fight_name,
            'draws': draws,
            'fights_out_of': fights_out_of,
            'height': height,
            'weight': weight,
            'reach': reach,
            'style': style
        }
        # Save HTML snapshot for future PNG download
        output_file = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}.png"

        html_output_path = f"templates/generated_cards/{output_file.replace('.png', '.html')}"
        os.makedirs(os.path.dirname(html_output_path), exist_ok=True)
        with open(html_output_path, "w", encoding="utf-8") as f:
            f.write(render_template(template_name, fighter=fighter_data))

        png_success, png_error = render_card_to_png(fighter_data, template_name=template_name, output_file=output_file)
        if not png_success:
            flash(f"Card created but PNG generation failed: {png_error}", 'warning')

        download_url = url_for('static', filename=f'generated/{output_file}')
        return render_template(template_name, fighter=fighter_data, download_url=download_url)

    except Exception as e:
        flash(f"An unexpected error occurred: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route("/download/<filename>")
def download_card(filename):
    file_path = os.path.join('static', 'generated', filename)
    if not os.path.exists(file_path):
        flash("Card image not found.", 'error')
        return redirect(url_for('index'))
    return send_from_directory('static/generated', filename, as_attachment=True)
    
    # Render HTML to PNG
    hti = Html2Image(output_path="static/generated")
    hti.screenshot(html_file=html_path, save_as=f"{filename}.png", size=(600, 900))  # Customize size as needed

    return send_file(output_path, as_attachment=True)

@app.errorhandler(413)
def too_large(e):
    flash("File is too large. Maximum size is 16MB.", 'error')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    flash("A server error occurred. Please try again.", 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
