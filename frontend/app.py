from flask import Flask, render_template, request, jsonify
import pymysql

app = Flask(__name__)

connection = pymysql.connect(
    host='localhost',
    user='root',
    password='Karamel2020',
    database='pizzadata'
)


@app.route('/')
def home():
    return render_template('index.html', page='home')


@app.route('/maps')
def maps():
    return render_template('index.html', page='maps')


@app.route('/pivot_charts', methods=['GET', 'POST'])
def pivot_charts():
    if request.method == 'POST':
        data_type = request.form.get('data_type')
        x_coord = request.form.get('x_coord')
        y_coord = request.form.get('y_coord')

        if data_type == 'pizza':
            query = f"SELECT DISTINCT name FROM products"
            with connection.cursor() as cursor:
                cursor.execute(query)
                product_names = [row[0] for row in cursor.fetchall()]

            # Add logic to fetch chart data based on x_coord and y_coord
            chart_data = []  # Replace with actual data fetching logic

            return jsonify(chart_data=chart_data, product_names=product_names)
        else:
            # Add logic to fetch restaurant data based on x_coord and y_coord
            chart_data = []  # Replace with actual data fetching logic

            return jsonify(chart_data=chart_data)
    return render_template('index.html', page='pivot_charts')


@app.route('/database', methods=['GET'])
def database():
    table = request.args.get('table', 'products')

    query = f"SELECT * FROM {table}"
    with connection.cursor() as cursor:
        cursor.execute(query)
        data = cursor.fetchall()

    return render_template('index.html', page='database', table=table, data=data)


if __name__ == '__main__':
    app.run(port=8080)
