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
    return render_template('index.html', page='home')

@app.route('/maps', methods=['GET'])
def maps():
    return render_template('maps.html', page='maps')

@app.route('/pivot_charts', methods=['GET', 'POST'])
def pivot_charts():
    if request.method == 'POST':
        data_type = request.form.get('data_type')

        logging.debug(f"Received POST data: data_type={data_type}")

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
        conn = get_db_connection()
        query = "SELECT storeID, latitude, longitude, city, state FROM stores"
        df = pd.read_sql(query, conn)

        store_data = df.to_dict(orient='records')
        return jsonify(store_data=store_data)
    except Exception as e:
        logging.error(f"Error in /store_locations endpoint: {e}")
        return jsonify({"error": "Error fetching store locations"}), 500
    finally:
        conn.close()

@app.route('/customer_locations', methods=['GET'])
def customer_locations():
    try:
        conn = get_db_connection()
        query = "SELECT latitude, longitude FROM customers"
        df = pd.read_sql(query, conn)

        customer_data = df.to_dict(orient='records')
        return jsonify(customer_data=customer_data)
    except Exception as e:
        logging.error(f"Error in /customer_locations endpoint: {e}")
        return jsonify({"error": "Error fetching customer locations"}), 500
    finally:
        conn.close()

@app.route('/ingredients', methods=['POST'])
def ingredients():
    sku = request.json.get('sku')
    size = request.json.get('size')

    try:
        conn = get_db_connection()
        query = """
        SELECT i.name AS Ingredient, pi.amount, i.cost_per_unit, (pi.amount * i.cost_per_unit / 100) as total_cost
        FROM pizza_ingredients pi
        JOIN ingredients i ON pi.ingredient_id = i.ingredient_id
        WHERE pi.sku = %s AND pi.size = %s
        """
        df = pd.read_sql(query, conn, params=[sku, size])

        if df.empty:
            return jsonify({"error": "No ingredients found for this pizza size"}), 400

        ingredients_data = df.to_dict(orient='records')
        total_cost = df['total_cost'].sum()
        price_query = "SELECT Price FROM pizza_profit_analysis WHERE SKU = %s AND Size = %s"
        price_df = pd.read_sql(price_query, conn, params=[sku, size])
        price = price_df.iloc[0]['Price']
        profit = price - total_cost

        response = {
            'ingredients_data': ingredients_data,
            'total_cost': round(total_cost, 2),
            'price': round(price, 2),
            'profit': round(profit, 2)
        }

        return jsonify(response)
    except Exception as e:
        logging.error(f"Error in /ingredients endpoint: {e}")
        return jsonify({"error": "Error fetching ingredients data"}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(port=8081, debug=True)
