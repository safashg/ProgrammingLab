from flask import Flask, render_template, request, jsonify
import pymysql
import pandas as pd
import logging

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

logging.basicConfig(level=logging.DEBUG)


def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='Pizzaservice123!',
        database='pizzadata'
    )
    return connection


def execute_query(query, params=None):
    """Hilfsfunktion zur Ausführung von SQL-Abfragen und Rückgabe als DataFrame"""
    try:
        conn = get_db_connection()
        if params:
            df = pd.read_sql(query, conn, params=params)
        else:
            df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        return None

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
                query = f"SELECT Name, Size, Price FROM {table}"
                df = pd.read_sql(query, conn)

                # Pivot-Tabelle erstellen
                pivot_df = df.pivot(index='Name', columns='Size', values='Price').fillna(0)

                chart_data = {
                    'labels': pivot_df.index.tolist(),
                    'datasets': []
                }

                for size in pivot_df.columns:
                    chart_data['datasets'].append({
                        'label': size,
                        'data': pivot_df[size].tolist()
                    })

                logging.debug(f"Chart data: {chart_data}")
                return jsonify(chart_data=chart_data)
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
    """Endpunkt für Standortdaten der Stores"""
    try:
        query = "SELECT storeID, latitude, longitude, city, state FROM stores"
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store locations"}), 500

        store_data = df.to_dict(orient='records')
        return jsonify(store_data=store_data)
    except Exception as e:
        logging.error(f"Error in /store_locations endpoint: {e}")
        return jsonify({"error": "Error fetching store locations"}), 500


@app.route('/customer_locations', methods=['GET'])
def customer_locations():
    """Endpunkt für Standortdaten der Kunden"""
    try:
        query = "SELECT latitude, longitude FROM customers"
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch customer locations"}), 500

        customer_data = df.to_dict(orient='records')
        return jsonify(customer_data=customer_data)
    except Exception as e:
        logging.error(f"Error in /customer_locations endpoint: {e}")
        return jsonify({"error": "Error fetching customer locations"}), 500


@app.route('/total_items_sold_per_store', methods=['GET'])
def total_items_sold_per_store():
    """Endpunkt für Gesamtverkaufszahlen pro Store"""
    try:
        query = """
        SELECT storeID, SUM(Quantity) AS totalItemsSold
        FROM store_pizza_sales
        GROUP BY storeID
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch total items sold data"}), 500

        total_items_data = df.to_dict(orient='records')
        return jsonify(total_items_data=total_items_data)
    except Exception as e:
        logging.error(f"Error in /total_items_sold_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching total items sold data"}), 500


@app.route('/store_sales_per_month', methods=['GET'])
def store_sales_per_month():
    """Endpunkt für Verkaufszahlen pro Monat"""
    try:
        query = """
        SELECT DATE_FORMAT(orderDate, '%Y-%m') AS month, SUM(Quantity) AS totalItemsSold
        FROM store_pizza_sales
        GROUP BY DATE_FORMAT(orderDate, '%Y-%m')
        ORDER BY DATE_FORMAT(orderDate, '%Y-%m')
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch sales per month data"}), 500

        store_monthly_sales_data = df.to_dict(orient='records')
        return jsonify(store_monthly_sales_data=store_monthly_sales_data)
    except Exception as e:
        logging.error(f"Error in /store_sales_per_month endpoint: {e}")
        return jsonify({"error": "Error fetching sales per month data"}), 500


@app.route('/store_revenue_and_profit_per_month', methods=['GET'])
def store_revenue_and_profit_per_month():
    """Endpunkt für Umsatz und Gewinn pro Monat"""
    try:
        query = """
        SELECT storeID, orderMonth, totalRevenue, totalProfit
        FROM monthly_store_revenue
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch revenue and profit data"}), 500

        store_revenue_profit_data = df.to_dict(orient='records')
        return jsonify(store_revenue_profit_data=store_revenue_profit_data)
    except Exception as e:
        logging.error(f"Error in /store_revenue_and_profit_per_month endpoint: {e}")
        return jsonify({"error": "Error fetching revenue and profit data"}), 500


@app.route('/store_orders_by_weekday', methods=['GET'])
def store_orders_by_weekday():
    # orders pro wochentag
    try:
        query = """
        SELECT storeID, DAYOFWEEK(orderDate) AS weekday, AVG(dailyOrders) AS avgDailyOrders
        FROM daily_store_orders
        GROUP BY storeID, DAYOFWEEK(orderDate)
        ORDER BY weekday
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch orders by weekday data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /orders_by_weekday endpoint: {e}")
        return jsonify({"error": "Error fetching orders by weekday data"}), 500


@app.route('/daily_order_stats', methods=['GET'])
def daily_order_stats():
    # tägliche Bestellstatistiken pro Store, Nützlich für Liniendiagramme zur Visualisierung von Bestelltrends
    try:
        query = """
            SELECT storeID, orderDate, NumberOfOrders, TotalItemsSold, AverageOrderValue
            FROM daily_store_order_stats
            ORDER BY orderDate
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch daily order stats"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /daily_order_stats endpoint: {e}")
        return jsonify({"error": "Error fetching daily order stats"}), 500


@app.route('/daily_average_order_value_per_store', methods=['GET'])
def daily_average_order_value_per_store():
    # durchschnittlichen Bestellwert pro Store, Nützlich für Balkendiagramme zur Darstellung der durchschnittlichen Bestellwerte.

    try:
        query = """
            SELECT storeID, AVG(AverageOrderValue) AS avgOrderValue
            FROM daily_store_order_stats
            GROUP BY storeID
            ORDER BY storeID
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average order value per store"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /average_order_value_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching average order value per store"}), 500


@app.route('/daily_order_intensity_heatmap', methods=['GET'])
def daily_order_intensity_heatmap():
    # Bestellintensitätsdaten, Nützlich für Heatmaps zur Visualisierung der Bestellintensität an verschiedenen Tagen.

    try:
        query = """
            SELECT storeID, orderDate, NumberOfOrders
            FROM daily_store_order_stats
            ORDER BY orderDate
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order intensity heatmap data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /order_intensity_heatmap endpoint: {e}")
        return jsonify({"error": "Error fetching order intensity heatmap data"}), 500


@app.route('/daily_order_trends', methods=['GET'])
def daily_order_trends():
    # Bestelltrends über Zeiträume hinweg, Nützlich für Bereichsdiagramme zur Darstellung der Entwicklung von Bestellungen, verkauften Artikeln und Bestellwerten
    try:
        query = """
            SELECT orderDate, SUM(NumberOfOrders) AS totalOrders, SUM(TotalItemsSold) AS totalItemsSold,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM daily_store_order_stats
            GROUP BY orderDate
            ORDER BY orderDate
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order trends data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /order_trends endpoint: {e}")
        return jsonify({"error": "Error fetching order trends data"}), 500


@app.route('/daily_store_performance_benchmark', methods=['GET'])
def daily_store_performance_benchmark():
    # Vergleicht die durchschnittliche Bestellleistung zwischen den Stores, Nützlich für Radar-Charts zur Darstellung der Store-Performance
    try:
        query = """
            SELECT storeID,
                   AVG(NumberOfOrders) AS avgNumberOfOrders,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM daily_store_order_stats
            GROUP BY storeID
            ORDER BY storeID
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store performance benchmark data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_performance_benchmark endpoint: {e}")
        return jsonify({"error": "Error fetching store performance benchmark data"}), 500



@app.route('/chart_data/top_customers', methods=['GET'])
def top_customers():
    """Endpunkt für die Top-Kunden nach Umsatz"""
    try:
        store_id = request.args.get('storeID')
        query = """
            SELECT customerID, total_spent
            FROM top_customers_per_store
            WHERE storeID = %s
            ORDER BY total_spent DESC
            LIMIT 10
        """
        df = execute_query(query, [store_id])
        if df is None:
            return jsonify({"error": "Failed to fetch top customers data"}), 500

        data = {
            "labels": df['customerID'].tolist(),
            "data": df['total_spent'].tolist()
        }
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error in /chart_data/top_customers endpoint: {e}")
        return jsonify({"error": "Error fetching top customers data"}), 500
@app.route('/chart_data/order_activity_over_time', methods=['GET'])
def order_activity_over_time():
    """Endpunkt für Bestellaktivität über Zeiträume hinweg"""
    try:
        store_id = request.args.get('storeID')
        interval = request.args.get('interval', 'week')  # Unterstützte Intervalle: 'day', 'week', 'month'

        if interval == 'day':
            query = """
                SELECT period, order_count
                FROM order_activity
                WHERE storeID = %s
                ORDER BY period;
            """
        elif interval == 'month':
            query = """
                SELECT DATE_FORMAT(period, '%Y-%m') AS period, SUM(order_count) AS order_count
                FROM order_activity
                WHERE storeID = %s
                GROUP BY DATE_FORMAT(period, '%Y-%m')
                ORDER BY DATE_FORMAT(period, '%Y-%m');
            """
        else:  # week
            query = """
                SELECT YEARWEEK(period, 1) AS period, SUM(order_count) AS order_count
                FROM order_activity
                WHERE storeID = %s
                GROUP BY YEARWEEK(period, 1)
                ORDER BY YEARWEEK(period, 1);
            """

        df = execute_query(query, [store_id])
        if df is None:
            return jsonify({"error": "Failed to fetch order activity data"}), 500

        data = {
            "labels": df['period'].tolist(),
            "data": df['order_count'].tolist()
        }
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error in /chart_data/order_activity_over_time endpoint: {e}")
        return jsonify({"error": "Error fetching order activity data"}), 500

if __name__ == '__main__':
    app.run(port=8085, debug=True)
