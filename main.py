from flask import Flask, render_template, request, redirect, session
import firebase_admin
from firebase_admin import credentials, firestore
from sms import send

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Güvenlik amacıyla kullanılacak bir anahtar

# Firebase'e bağlanmak için gerekli yapılandırma
cred = credentials.Certificate('./serviceAccountKey.json')  # serviceAccountKey.json dosyasının yolu
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_ref = db.collection('users').document(username)
        user = user_ref.get()

        if user.exists:
            return "Bu kullanıcı adı zaten kullanımda. Lütfen başka bir kullanıcı adı seçin."
        else:
            users_ref = db.collection('users')
            doc_ref = users_ref.document(username)
            doc_ref.set({
                'password': password,
                'balance': 0,
                'status': 'user'  # Yeni kayıt olan kullanıcıların varsayılan durumu
            })
            return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_ref = db.collection('users').document(username)
        user = user_ref.get()
        if user.exists:
            user_data = user.to_dict()
            if user_data['password'] == password:
                session['username'] = username
                return redirect('/dashboard')
            else:
                return "Yanlış şifre. Lütfen tekrar deneyin."
        else:
            return "Kullanıcı bulunamadı."
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    deducted = False  # Deduction işlemi gerçekleşti mi?
    if 'username' in session:
        username = session['username']
        user_ref = db.collection('users').document(username)
        user = user_ref.get()
        if user.exists:
            user_data = user.to_dict()
            balance = user_data['balance']

            if request.method == 'POST':
                if int(balance) >= 10:
                    new_balance = int(balance) - 10
                    user_ref.update({'balance': new_balance})
                    number = int(request.form['number'])
                    send(number,100,99)
                    deducted = True  # Deduction işlemi gerçekleşti
                else:
                    return "Insufficient balance. Your balance is less than $10."

            return render_template('dashboard.html', username=username, balance=balance, deducted=deducted)
        else:
            return "User not found."
    return redirect('/login')
@app.route('/about_me')
def about_me():
    if 'username' in session:
        username = session['username']
        user_ref = db.collection('users').document(username)
        user = user_ref.get()
        if user.exists:
            user_data = user.to_dict()
            return render_template('about_me.html', username=username, balance=user_data['balance'], status=user_data['status'], password=user_data['password'])
        else:
            return "User not found."
    return redirect('/login')
@app.route('/adminpanel')
def admin_panel():
    if 'username' in session:
        username = session['username']
        user_ref = db.collection('users').document(username)
        user = user_ref.get()

        if user.exists:
            user_data = user.to_dict()
            balance = user_data['balance']
            if user_data['status'] == 'admin':
                users_ref = db.collection('users')
                all_users = users_ref.stream()  # Tüm kullanıcıları almak için stream() fonksiyonu kullanılır.
                return render_template('admin_panel.html', username=username, all_users=all_users,balance=balance)
            elif user_data['status'] == 'vip':
                users_ref = db.collection('users')
                all_users = users_ref.stream()  # Tüm kullanıcıları almak için stream() fonksiyonu kullanılır.
                return render_template('vip_admin.html', username=username, all_users=all_users,balance=balance)
            else:
                return "Bu sayfaya erişim izniniz yok!"
    return redirect('/login')

@app.route('/edit/<username>', methods=['GET', 'POST'])
def edit_user(username):
    if 'username' in session:
        admin_username = session['username']
        user_ref = db.collection('users').document(admin_username)
        user = user_ref.get()
        if user.exists:
            user_data = user.to_dict()
            if user_data['status'] == 'admin' or user_data["status"] == "vip":
                user_ref = db.collection('users').document(username)
                user = user_ref.get()
                if user.exists:
                    user_data = user.to_dict()
                    if request.method == 'POST':
                        new_password = request.form['password']
                        new_balance = request.form['balance']
                        new_status = request.form['status']
                        user_ref.update({
                            'password': new_password,
                            'balance': new_balance,
                            'status': new_status
                        })
                        return redirect('/adminpanel')
                    return render_template('edit_user.html', admin_username=admin_username, user_data=user_data)
                else:
                    return "Kullanıcı bulunamadı."
            else:
                return "Bu işlem için yetkiniz yok!"
    return redirect('/login')

@app.route('/delete/<username>')
def delete_user(username):
    if 'username' in session:
        admin_username = session['username']
        user_ref = db.collection('users').document(admin_username)
        user = user_ref.get()
        if user.exists:
            user_data = user.to_dict()
            if user_data['status'] == 'admin':
                user_ref = db.collection('users').document(username)
                user = user_ref.get()
                if user.exists:
                    user_ref.delete()
                    return redirect('/adminpanel')
                else:
                    return "Kullanıcı bulunamadı."
            else:
                return "Bu işlem için yetkiniz yok!"
    return redirect('/login')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0")
