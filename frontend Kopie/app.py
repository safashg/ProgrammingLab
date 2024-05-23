from flask import Flask, render_template, request, jsonify
import pymysql
import pandas as pd
import logging

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='Karamel2020',
        database='pizzadata'
    )
    return connection

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', page='home')

@app.route('/maps', methods=['GET'])
def maps():
    return render_template('maps.html', page='maps')

@app.route('/pivot_charts', methods=['GET', 'POST'])
def pivot_charts():
    if request.method == 'POST':
        data_type = request.form.get('data_type')
        x_coord = request.form.get('x_coord')
        y_coord = request.form.get('y_coord')

        logging.debug(f"Received POST data: data_type={data_type}, x_coord={x_coord}, y_coord={y_coord}")

        try:
            conn = get_db_connection()
            if data_type == 'pizza':
                table = 'products'
            elif data_type == 'restaurant':
                table = 'total_spent'
            else:
                return jsonify({"error": "Invalid data type"}), 400

            query = f"SELECT {x_coord}, {y_coord} FROM {table}"
            df = pd.read_sql(query, conn)

            chart_data = df.to_dict(orient='records')
            logging.debug(f"Chart data: {chart_data}")
            return jsonify(chart_data=chart_data)
        except Exception as e:
            logging.error(f"Error in /pivot_charts endpoint: {e}")
            # Instead of returning a JSON error response, redirect to an error page or render an error template
            return render_template('error.html', error_message="Error fetching chart data")
        finally:
            conn.close()

    return render_template('pivot_charts.html')

@app.route('/database', methods=['GET'])
def database():
    table = request.args.get('table', 'products')

    try:
        conn = get_db_connection()
        if table in ['products', 'total_spent']:
            query = f"SELECT * FROM {table}"
            with conn.cursor() as cursor:
                cursor.execute(query)
                data = cursor.fetchall()

            return render_template('database.html', table=table, data=data)
        else:
            return render_template('error.html', error_message="Invalid table name")
    except Exception as e:
        logging.error(f"Error in /database endpoint: {e}")
        return render_template('error.html', error_message="Error fetching data")
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(port=8081, debug=True)
