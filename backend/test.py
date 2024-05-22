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

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/chart')
def chart():
    try:
        conn = get_db_connection()
        query = '''
        SELECT * FROM monthly_store_orders
        '''
        df = pd.read_sql(query, conn)
        conn.close()

        df['monthYear'] = pd.to_datetime(df['monthYear'], format='%Y-%m')
        df = df.sort_values(by=['storeID', 'monthYear'])

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

if __name__ == '__main__':
    app.run(port=8080, debug=True)
