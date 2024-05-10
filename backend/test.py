from flask import Flask, render_template, request
import pymysql

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='Pizzaservice123!',
        database='pizzadata'
    )
    return connection

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_option = request.form['selection']
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if selected_option == 'Stores':
                cursor.execute("SELECT * FROM stores")
                results = cursor.fetchall()
            elif selected_option == 'Products':
                cursor.execute("SELECT * FROM products WHERE Size='Medium'")
                results = cursor.fetchall()
            elif selected_option == 'Revenue':
                cursor.execute("SELECT * FROM store_revenue")
                results = cursor.fetchall()
        conn.close()
        return render_template('index.html', selection=selected_option, results=results)
    return render_template('index.html', selection=None, results=None)

if __name__ == '__main__':
    app.run(port=8080)
    app.run(debug=True)
