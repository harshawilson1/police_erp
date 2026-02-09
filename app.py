from flask import Flask, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
app = Flask(__name__)
app.secret_key = 'police_erp_secret'

# ---------- MySQL Configuration ----------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root123'
app.config['MYSQL_DB'] = 'police_erp'

mysql = MySQL(app)

# ---------- LOGIN ----------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT role FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cur.fetchone()
        cur.close()

        if user:
            session['role'] = user[0]
            session['username'] = username
            return redirect('/dashboard')

    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    return render_template('dashboard.html')

# ---------- ADD FIR ----------
@app.route('/add_fir', methods=['GET', 'POST'])
def add_fir():
    if 'username' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    # Dropdown data (crime & station stay as dropdowns)
    cur.execute("SELECT crime_id, crime_type FROM crime")
    crimes = cur.fetchall()

    cur.execute("SELECT station_id, station_name FROM police_station")
    stations = cur.fetchall()

    if request.method == 'POST':
        # Citizen data from textbox
        citizen_name = request.form['citizen_name']
        citizen_phone = request.form['citizen_phone']
        citizen_address = request.form['citizen_address']

        # Insert citizen
        cur.execute(
            "INSERT INTO citizen (name, phone, address) VALUES (%s, %s, %s)",
            (citizen_name, citizen_phone, citizen_address)
        )
        citizen_id = cur.lastrowid  # 👈 VERY IMPORTANT

        # FIR data
        crime_id = request.form['crime_id']
        station_id = request.form['station_id']
        status = request.form['status']

        # Insert FIR
        cur.execute(
            """INSERT INTO fir
               (citizen_id, crime_id, station_id, fir_date, status)
               VALUES (%s, %s, %s, CURDATE(), %s)""",
            (citizen_id, crime_id, station_id, status)
        )

        mysql.connection.commit()
        cur.close()
        return redirect('/view_fir')

    cur.close()
    return render_template(
        'add_fir.html',
        crimes=crimes,
        stations=stations
    )

# ---------- VIEW FIR ----------
@app.route('/view_fir')
def view_fir():
    if 'username' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.fir_id, c.name, cr.crime_type, f.status
        FROM fir f
        JOIN citizen c ON f.citizen_id = c.citizen_id
        JOIN crime cr ON f.crime_id = cr.crime_id
    """)
    firs = cur.fetchall()
    cur.close()

    return render_template('view_fir.html', firs=firs)

# ---------- EDIT FIR ----------
@app.route('/edit_fir/<int:fir_id>', methods=['GET', 'POST'])
def edit_fir(fir_id):
    if 'username' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        status = request.form['status']
        cur.execute(
            "UPDATE fir SET status=%s WHERE fir_id=%s",
            (status, fir_id)
        )
        mysql.connection.commit()
        cur.close()
        return redirect('/view_fir')

    cur.execute("SELECT * FROM fir WHERE fir_id=%s", (fir_id,))
    fir = cur.fetchone()
    cur.close()

    return render_template('edit_fir.html', fir=fir)

# ---------- DELETE FIR (ADMIN ONLY) ----------
@app.route('/delete_fir/<int:fir_id>')
def delete_fir(fir_id):
    if session.get('role') != 'ADMIN':
        return "Access Denied"

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM fir WHERE fir_id=%s", (fir_id,))
    mysql.connection.commit()
    cur.close()

    return redirect('/view_fir')

# ---------- STORED PROCEDURE REPORT ----------
@app.route('/station_report')
def station_report():
    if 'username' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()
    cur.callproc('get_station_case_count')
    data = cur.fetchall()
    cur.close()

    return render_template('report.html', data=data)

@app.route('/citizen_register', methods=['GET', 'POST'])
def citizen_register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()

        # Insert into citizen table
        cur.execute(
            "INSERT INTO citizen (name, phone, address) VALUES (%s, %s, %s)",
            (name, phone, address)
        )
        citizen_id = cur.lastrowid

        # Insert login credentials
        cur.execute(
            "INSERT INTO citizen_users (citizen_id, username, password) VALUES (%s, %s, %s)",
            (citizen_id, username, password)
        )

        mysql.connection.commit()
        cur.close()

        return redirect('/citizen_login')

    return render_template('citizen_register.html')


@app.route('/citizen_login', methods=['GET', 'POST'])
def citizen_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(
            "SELECT * FROM citizen_users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cur.fetchone()
        cur.close()

        if user:
            session['citizen_id'] = user['citizen_id']
            session['citizen_user_id'] = user['citizen_user_id']
            return redirect('/citizen_dashboard')
        else:
            return render_template('citizen_login.html', error="Invalid login")

    return render_template('citizen_login.html')
@app.route('/citizen_dashboard')
def citizen_dashboard():
    if 'citizen_id' not in session:
        return redirect('/citizen_login')

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute(
        "SELECT * FROM citizen WHERE citizen_id=%s",
        (session['citizen_id'],)
    )
    citizen = cur.fetchone()
    cur.close()

    return render_template('citizen_dashboard.html', citizen=citizen)
@app.route('/citizen_logout')
def citizen_logout():
    session.clear()
    return redirect('/citizen_login')

@app.route('/test_ui')
def test_ui():
    return render_template('test_ui.html')

# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True)
