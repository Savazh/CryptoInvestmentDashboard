from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    crypto_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Float, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def fetch_crypto_price(crypto_name):
    params = {"ids": crypto_name, "vs_currencies": "usd"}
    try:
        response = requests.get(COINGECKO_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get(crypto_name, {}).get("usd", None)
    except requests.exceptions.RequestException:
        return None

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/portfolio')
@login_required
def portfolio():
    portfolio_items = Portfolio.query.filter_by(user_id=current_user.id).all()
    total_value = 0
    portfolio_data = []

    for item in portfolio_items:
        price = fetch_crypto_price(item.crypto_name)
        if price:
            value = price * item.quantity
            total_value += value
            portfolio_data.append({
                "crypto_id": item.id,
                "crypto_name": item.crypto_name,
                "quantity": item.quantity,
                "price": price,
                "value": value,
            })

    return render_template(
        'portfolio.html',
        portfolio=portfolio_data,
        total_value=total_value
    )

@app.route('/add_crypto', methods=['GET', 'POST'])
@login_required
def add_crypto():
    if request.method == 'POST':
        crypto_name = request.form.get('crypto_name').lower()
        quantity = float(request.form.get('quantity'))
        new_crypto = Portfolio(user_id=current_user.id, crypto_name=crypto_name, quantity=quantity)
        db.session.add(new_crypto)
        db.session.commit()
        flash(f"Added {quantity} {crypto_name} to your portfolio.")
        return redirect(url_for('portfolio'))
    return render_template('add_crypto.html')

@app.route('/delete_crypto/<int:crypto_id>')
@login_required
def delete_crypto(crypto_id):
    crypto = Portfolio.query.get_or_404(crypto_id)
    if crypto.user_id != current_user.id:
        flash("Unauthorized action.")
        return redirect(url_for('portfolio'))
    db.session.delete(crypto)
    db.session.commit()
    flash(f"Deleted {crypto.crypto_name} from your portfolio.")
    return redirect(url_for('portfolio'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)