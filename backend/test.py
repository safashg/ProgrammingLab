from flask import Flask, render_template, request, jsonify
import pymysql
import pandas as pd
import logging

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='Pizzaservice123!',
        database='pizzadata'
    )
    return connection

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/pivot_charts', methods=['GET', 'POST'])
def pivot_charts():
    if request.method == 'POST':
        data_type = request.form.get('data_type')
        x_coord = request.form.get('x_coord')
        y_coord = request.form.get('y_coord')

        conn = get_db_connection()
        if data_type == 'restaurant':
            query = f"SELECT {x_coord}, {y_coord} FROM products"
        elif data_type == 'pizza':
            query = f"SELECT {x_coord}, {y_coord} FROM pizza_profit_analysis"
        else:
            return jsonify({"error": "Invalid data type"}), 400

        df = pd.read_sql(query, conn)
        conn.close()

        chart_data = df.to_dict(orient='records')
        return jsonify(chart_data=chart_data)

    return render_template('pivot_charts.html')

@app.route('/chart')
def chart():
    try:
        conn = get_db_connection()
        query = '''
        SELECT * FROM monthly_store_revenue
        '''
        df = pd.read_sql(query, conn)
        conn.close()

        df['orderMonth'] = pd.to_datetime(df['orderMonth'], format='%Y-%m')
        df = df.sort_values(by=['storeID', 'orderMonth'])

        data = df.to_dict(orient='records')
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error in /chart endpoint: {e}")
        return jsonify({"error": "Error fetching chart data"}), 500

@app.route('/store/<int:store_id>')
def store_info(store_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM stores WHERE storeID = %s", (store_id,))
        store_details = cursor.fetchone()
        conn.close()

        if store_details:
            return jsonify(store_details)
        else:
            return jsonify({"error": "Store not found"}), 404
    except Exception as e:
        logging.error(f"Error in /store/{store_id} endpoint: {e}")
        return jsonify({"error": "Error fetching store information"}), 500

@app.route('/get_chart_data/<string:chart_type>', methods=['GET'])
def get_chart_data(chart_type):
    try:
        conn = get_db_connection()
        if chart_type == 'weekly_revenue':
            query = "SELECT * FROM weekly_store_revenue"
        elif chart_type == 'monthly_revenue':
            query = "SELECT * FROM monthly_store_revenue"
        elif chart_type == 'daily_orders':
            query = "SELECT * FROM daily_store_orders"
        else:
            return jsonify({"error": "Invalid chart type"}), 400

        df = pd.read_sql(query, conn)
        conn.close()

        data = df.to_dict(orient='records')
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error in /get_chart_data/{chart_type} endpoint: {e}")
        return jsonify({"error": "Error fetching chart data"}), 500

if __name__ == '__main__':
    app.run(port=8080, debug=True)
