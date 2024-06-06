from flask import Flask, render_template, request, jsonify
import pymysql
import pandas as pd
import logging

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Update the get_db_connection function to use pymysql
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

@app.route('/maps', methods=['GET'])
def maps():
    return render_template('maps.html')


@app.route('/pivot_charts', methods=['GET', 'POST'])
def pivot_charts():
    if request.method == 'POST':
        data_type = request.form.get('data_type')
        x_coord = request.form.get('x_coord', 'default_x')
        y_coord = request.form.get('y_coord', 'default_y')

        logging.debug(f"Received POST data: data_type={data_type}, x_coord={x_coord}, y_coord={y_coord}")

        try:
            conn = get_db_connection()
            if data_type == 'pizza':
                table = 'pizza_profit_analysis'
                query = f"SELECT SKU, Name AS Category, Size, Price, Profit FROM {table}"
            elif data_type == 'restaurant':
                table = 'total_items_sold'
                query = f"SELECT {x_coord}, {y_coord} FROM {table}"
            elif data_type == 'profit':
                table = 'pizza_profit_analysis'
                query = f"SELECT {x_coord}, {y_coord} FROM {table}"
            elif data_type == 'monthly_revenue':
                table = 'monthly_store_revenue'
                x_coord = 'orderMonth'
                y_coord = 'totalRevenue'
                query = f"SELECT {x_coord}, {y_coord}, storeID FROM {table}"
            else:
                return jsonify({"error": "Invalid data type"}), 400

            df = pd.read_sql(query, conn)

            chart_data = df.to_dict(orient='records')
            logging.debug(f"Chart data: {chart_data}")
            return jsonify(chart_data=chart_data)
        except Exception as e:
            logging.error(f"Error in /pivot_charts endpoint: {e}")
            return render_template('error.html', error_message="Error fetching chart data")
        finally:
            conn.close()

    return render_template('pivot_charts.html')

@app.route('/store_locations', methods=['GET'])
def store_locations():
    try:
        connection = get_db_connection()
        query = "SELECT storeID, latitude, longitude, city, state FROM stores"
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(result, columns=columns)
        connection.close()

        store_data = df.to_dict(orient='records')
        return jsonify(store_data=store_data)
    except Exception as e:
        logging.error(f"Error in /store_locations endpoint: {e}")
        return jsonify({"error": "Error fetching store locations"}), 500

@app.route('/customer_locations', methods=['GET'])
def customer_locations():
    try:
        connection = get_db_connection()
        query = "SELECT latitude, longitude FROM customers"
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(result, columns=columns)
        connection.close()

        customer_data = df.to_dict(orient='records')
        return jsonify(customer_data=customer_data)
    except Exception as e:
        logging.error(f"Error in /customer_locations endpoint: {e}")
        return jsonify({"error": "Error fetching customer locations"}), 500

@app.route('/total_items_sold_per_store', methods=['GET'])
def total_items_sold_per_store():
    store_id = request.args.get('storeID')
    try:
        connection = get_db_connection()
        query = """
        SELECT storeID, SUM(Quantity) AS totalItemsSold
        FROM store_pizza_sales
        WHERE storeID = %s
        GROUP BY storeID
        """
        with connection.cursor() as cursor:
            cursor.execute(query, (store_id,))
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(result, columns=columns)
        connection.close()

        total_items_data = df.to_dict(orient='records')
        return jsonify(total_items_data=total_items_data)
    except Exception as e:
        logging.error(f"Error in /total_items_sold_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching total items sold data"}), 500



if __name__ == '__main__':
    app.run(port=8085, debug=True)
