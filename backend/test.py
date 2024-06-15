from flask import Flask, render_template, request, jsonify
import pymysql
import pandas as pd
import logging
from sqlalchemy import create_engine



app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

logging.basicConfig(level=logging.DEBUG)

# Update your database connection URI as needed
DATABASE_URI = 'mysql+pymysql://root:HossiundJazzy3@localhost/pizzadaten'

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URI)



def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='HossiundJazzy3',
        database='pizzadaten'
    )
    return connection


def execute_query(query, params=None):
    """Hilfsfunktion zur Ausführung von SQL-Abfragen und Rückgabe als DataFrame"""
    try:
        with get_db_connection() as conn:
            if params:
                df = pd.read_sql(query, conn, params=params)
            else:
                df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        return None



@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/sales', methods=['GET'])
def sales():
    return render_template('sales.html')





@app.route('/sales_data', methods=['GET'])
def sales_data():
    try:
        store_id = request.args.get('storeID')
        pizza_type = request.args.get('pizzaType')

        query = """
            SELECT orderDate, ProductName, SUM(Quantity) AS totalQuantity
            FROM daily_store_pizza_sales
        """

        conditions = []
        params = {}

        if store_id:
            conditions.append("storeID = %(storeID)s")
            params['storeID'] = store_id

        if pizza_type:
            conditions.append("ProductName = %(pizzaType)s")
            params['pizzaType'] = pizza_type

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += """
            GROUP BY orderDate, ProductName
            ORDER BY orderDate, ProductName;
        """

        df = pd.read_sql(query, engine, params=params)
        if df is None:
            return jsonify({"error": "Failed to fetch sales data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /sales_data endpoint: {e}")
        return jsonify({"error": "Error fetching sales data"}), 500


@app.route('/weekly_sales_data', methods=['GET'])
def weekly_sales_data():
    try:
        store_id = request.args.get('storeID')
        pizza_type = request.args.get('pizzaType')

        query = """
            SELECT yearWeek AS orderDate, PizzaName, SUM(Quantity) AS totalQuantity
            FROM weekly_store_pizza_sales
        """

        conditions = []
        params = {}

        if store_id:
            conditions.append("storeID = %(storeID)s")
            params['storeID'] = store_id

        if pizza_type:
            conditions.append("PizzaName = %(pizzaType)s")
            params['pizzaType'] = pizza_type

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += """
            GROUP BY yearWeek, PizzaName
            ORDER BY yearWeek, PizzaName;
        """

        df = pd.read_sql(query, engine, params=params)
        if df is None:
            return jsonify({"error": "Failed to fetch weekly sales data"}), 500

        # Format yearWeek to a datetime object for correct plotting
        df['orderDate'] = pd.to_datetime(df['orderDate'] + '0', format='%Y-%W%w')
        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_sales_data endpoint: {e}")
        return jsonify({"error": "Error fetching weekly sales data"}), 500








@app.route('/get_stores', methods=['GET'])
def get_stores():
    try:
        query = "SELECT DISTINCT storeID FROM stores"
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(stores=data)
    except Exception as e:
        logging.error(f"Error in /get_stores endpoint: {e}")
        return jsonify({"error": "Error fetching store data"}), 500

@app.route('/get_pizza_types', methods=['GET'])
def get_pizza_types():
    try:
        query = "SELECT DISTINCT ProductName FROM daily_store_pizza_sales"
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch pizza types data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(pizzaTypes=data)
    except Exception as e:
        logging.error(f"Error in /get_pizza_types endpoint: {e}")
        return jsonify({"error": "Error fetching pizza types data"}), 500




@app.route('/customer', methods=['GET'])
def customer():
    return render_template('customer.html')


@app.route('/maps', methods=['GET'])
def maps():
    return render_template('maps.html')


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


# store analyse

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


# Endpoint für orders by weekday
@app.route('/store_orders_by_weekday', methods=['GET'])
def store_orders_by_weekday():
    """Endpunkt für Bestellungen pro Wochentag pro Store"""
    try:
        query = """
        SELECT Weekday, storeID, SUM(NumberOfOrders) AS totalOrders
        FROM OrdersPerWeekday
        GROUP BY Weekday, storeID
        ORDER BY Weekday, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch orders by weekday data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_orders_by_weekday endpoint: {e}")
        return jsonify({"error": "Error fetching orders by weekday data"}), 500


@app.route('/order_activity_over_time', methods=['GET'])
def order_activity_over_time():
    """Endpunkt für Bestellaktivität über Zeiträume hinweg"""
    try:
        interval = request.args.get('interval',
                                    'week')  # Unterstützte Intervalle: 'day', 'week', 'month' -> ein diagramm wo der benutzer interaktiv entschiedet was er angezeigt haben möchte

        if interval == 'day':
            query = """
                SELECT storeID, DATE(period) AS period, SUM(order_count) AS order_count
                FROM order_activity
                GROUP BY storeID, DATE(period)
                ORDER BY storeID, DATE(period);
            """
        elif interval == 'month':
            query = """
                SELECT storeID, DATE_FORMAT(period, '%Y-%m') AS period, SUM(order_count) AS order_count
                FROM order_activity
                GROUP BY storeID, DATE_FORMAT(period, '%Y-%m')
                ORDER BY storeID, DATE_FORMAT(period, '%Y-%m');
            """
        else:  # week
            query = """
                SELECT storeID, YEARWEEK(period, 1) AS period, SUM(order_count) AS order_count
                FROM order_activity
                GROUP BY storeID, YEARWEEK(period, 1)
                ORDER BY storeID, YEARWEEK(period, 1);
            """

        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order activity data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /order_activity_over_time endpoint: {e}")
        return jsonify({"error": "Error fetching order activity data"}), 500


@app.route('/store_sales_per_month', methods=['GET'])
def store_sales_per_month():
    # Endpunkt für Verkaufszahlen pro Monat
    try:
        query = """
       SELECT storeID, DATE_FORMAT(orderDate, '%Y-%m') AS month, SUM(Quantity) AS totalItemsSold
        FROM store_pizza_sales
        GROUP BY storeID, DATE_FORMAT(orderDate, '%Y-%m')
        ORDER BY storeID, DATE_FORMAT(orderDate, '%Y-%m')
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


@app.route('/weekly_order_stats', methods=['GET'])
def weekly_order_stats():
    # Wöchentliche Bestellstatistiken pro Store, nützlich für Liniendiagramme zur Visualisierung von Bestelltrends
    try:
        query = """
                SELECT storeID, weekYear, NumberOfOrders, TotalItemsSold, AverageOrderValue
                FROM weekly_store_order_stats
                ORDER BY weekYear
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch weekly order stats"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_order_stats endpoint: {e}")
        return jsonify({"error": "Error fetching weekly order stats"}), 500


@app.route('/weekly_average_order_value_per_store', methods=['GET'])
def weekly_average_order_value_per_store():
    # Durchschnittlicher Bestellwert pro Store, Nützlich für Balkendiagramme zur Darstellung der durchschnittlichen Bestellwerte.

    try:
        query = """
                SELECT storeID, AVG(AverageOrderValue) AS avgOrderValue
                FROM weekly_store_order_stats
                GROUP BY storeID
                ORDER BY storeID
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average order value per store"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_average_order_value_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching average order value per store"}), 500


@app.route('/weekly_order_intensity', methods=['GET'])
def weekly_order_intensity_heatmap():
    # Bestellintensitätsdaten, Nützlich für Heatmaps zur Visualisierung der Bestellintensität an verschiedenen Wochen.

    try:
        query = """
                SELECT storeID, weekYear, NumberOfOrders
                FROM weekly_store_order_stats
                ORDER BY weekYear
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order intensity heatmap data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_order_intensity endpoint: {e}")
        return jsonify({"error": "Error fetching order intensity data"}), 500


@app.route('/weekly_order_trends', methods=['GET'])
def weekly_order_trends():
    # Bestelltrends über Zeiträume hinweg, Nützlich für Bereichsdiagramme zur Darstellung der Entwicklung von Bestellungen, verkauften Artikeln und Bestellwerten.
    try:
        query = """
            SELECT weekYear, SUM(NumberOfOrders) AS totalOrders, SUM(TotalItemsSold) AS totalItemsSold,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM weekly_store_order_stats
            GROUP BY weekYear
            ORDER BY weekYear
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order trends data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_order_trends endpoint: {e}")
        return jsonify({"error": "Error fetching order trends data"}), 500


@app.route('/weekly_store_performance_benchmark', methods=['GET'])
def weekly_store_performance_benchmark():
    # Vergleicht die durchschnittliche Bestellleistung zwischen den Stores, nützlich für Radar-Charts zur Darstellung der Store-Performance
    try:
        query = """
            SELECT storeID,
                   AVG(NumberOfOrders) AS avgNumberOfOrders,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM weekly_store_order_stats
            GROUP BY storeID
            ORDER BY storeID
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store performance benchmark data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_store_performance_benchmark endpoint: {e}")
        return jsonify({"error": "Error fetching store performance benchmark data"}), 500


@app.route('/monthly_order_stats', methods=['GET'])
def monthly_order_stats():
    # Monatliche Bestellstatistiken pro Store, nützlich für Liniendiagramme zur Visualisierung von Bestelltrends
    try:
        query = """
                SELECT storeID, monthYear, NumberOfOrders, TotalItemsSold, AverageOrderValue
                FROM monthly_store_order_stats
                ORDER BY monthYear
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch monthly order stats"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_order_stats endpoint: {e}")
        return jsonify({"error": "Error fetching monthly order stats"}), 500


@app.route('/monthly_average_order_value_per_store', methods=['GET'])
def monthly_average_order_value_per_store():
    # Durchschnittlicher Bestellwert pro Store, nützlich für Balkendiagramme zur Darstellung der durchschnittlichen Bestellwerte.

    try:
        query = """
                SELECT storeID, AVG(AverageOrderValue) AS avgOrderValue
                FROM monthly_store_order_stats
                GROUP BY storeID
                ORDER BY storeID
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average order value per store"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_average_order_value_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching average order value per store"}), 500


@app.route('/monthly_order_intensity', methods=['GET'])
def monthly_order_intensity_heatmap():
    # Bestellintensitätsdaten, nützlich für Heatmaps zur Visualisierung der Bestellintensität an verschiedenen Monaten.

    try:
        query = """
                SELECT storeID, monthYear, NumberOfOrders
                FROM monthly_store_order_stats
                ORDER BY monthYear
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order intensity data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_order_intensity endpoint: {e}")
        return jsonify({"error": "Error fetching order intensity data"}), 500


@app.route('/monthly_store_performance_benchmark', methods=['GET'])
def monthly_store_performance_benchmark():
    # Vergleicht die durchschnittliche Bestellleistung zwischen den Stores, nützlich für Radar-Charts zur Darstellung der Store-Performance
    try:
        query = """
            SELECT storeID,
                   AVG(NumberOfOrders) AS avgNumberOfOrders,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM monthly_store_order_stats
            GROUP BY storeID
            ORDER BY storeID
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store performance benchmark data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_store_performance_benchmark endpoint: {e}")
        return jsonify({"error": "Error fetching store performance benchmark data"}), 500


@app.route('/monthly_order_trends', methods=['GET'])
def monthly_order_trends():
    # Bestelltrends über Zeiträume hinweg, nützlich für Bereichsdiagramme zur Darstellung der Entwicklung von Bestellungen, verkauften Artikeln und Bestellwerten.
    try:
        query = """
            SELECT monthYear, SUM(NumberOfOrders) AS totalOrders, SUM(TotalItemsSold) AS totalItemsSold,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM monthly_store_order_stats
            GROUP BY monthYear
            ORDER BY monthYear
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order trends data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_order_trends endpoint: {e}")
        return jsonify({"error": "Error fetching order trends data"}), 500


@app.route('/unique_customers_per_store_table', methods=['GET'])
def unique_customers_per_store_table():
    """Endpunkt zur Abfrage der Tabelle wie viele customers per store"""
    try:
        query = """
            SELECT storeID, uniqueCustomers
            FROM unique_customers_per_store
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch unique customers per store data from table"}), 500

        unique_customers_data = df.to_dict(orient='records')
        return jsonify(unique_customers_data=unique_customers_data)
    except Exception as e:
        logging.error(f"Error in /unique_customers_per_store_table endpoint: {e}")
        return jsonify({"error": "Error fetching unique customers per store data from table"}), 500


@app.route('/category_share_per_store', methods=['GET'])
def category_share_per_store():
    """Endpunkt für den Anteil der Kategorien pro Store"""
    try:
        query = """
            SELECT storeID, Category, NumberOfPizzasSold,
                   ROUND(100.0 * NumberOfPizzasSold / SUM(NumberOfPizzasSold) OVER(PARTITION BY storeID), 2) AS Percentage
            FROM PizzaSalesSummary
            ORDER BY storeID, Category;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch category share per store data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /category_share_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching category share per store data"}), 500


@app.route('/category_sales_comparison', methods=['GET'])
def category_sales_comparison():
    """Endpunkt für den Vergleich der Kategorie-Verkäufe zwischen Stores"""
    try:
        query = """
            SELECT Category, storeID, NumberOfPizzasSold
            FROM PizzaSalesSummary
            ORDER BY Category, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch category sales comparison data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /category_sales_comparison endpoint: {e}")
        return jsonify({"error": "Error fetching category sales comparison data"}), 500


@app.route('/top_categories_per_store', methods=['GET'])
def top_categories_per_store():
    """Endpunkt für die Top-Kategorien pro Store"""
    try:
        query = """
            SELECT storeID, Category, NumberOfPizzasSold
            FROM PizzaSalesSummary
            WHERE (storeID, NumberOfPizzasSold) IN (
                SELECT storeID, MAX(NumberOfPizzasSold)
                FROM PizzaSalesSummary
                GROUP BY storeID
            )
            ORDER BY storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch top categories per store data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /top_categories_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching top categories per store data"}), 500


@app.route('/seasonal_order_analysis', methods=['GET'])
def seasonal_order_analysis():
    """Endpunkt für die Analyse saisonaler Bestellungen"""
    try:
        query = """
            SELECT 
                OrderDate, 
                storeID, 
                TotalOrders,
                EXTRACT(MONTH FROM OrderDate) AS Month,
                EXTRACT(DAY FROM OrderDate) AS Day
            FROM TopOrderDates
            ORDER BY TotalOrders DESC, OrderDate, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch seasonal order analysis data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /seasonal_order_analysis endpoint: {e}")
        return jsonify({"error": "Error fetching seasonal order analysis data"}), 500


@app.route('/holiday_order_analysis', methods=['GET'])
def holiday_order_analysis():
    """Endpunkt für die Analyse von Bestellungen an Feiertagen"""
    try:
        holidays = [
            '2021-01-01', '2021-01-18', '2021-02-15', '2021-04-02', '2021-04-04', '2021-05-31', '2021-06-19',
            '2021-07-04', '2021-09-06', '2021-10-11', '2021-11-11', '2021-11-25', '2021-12-24', '2021-12-25',
            '2021-12-31',
            '2022-01-01', '2022-01-17', '2022-02-21', '2022-04-15', '2022-04-17', '2022-05-30', '2022-06-19',
            '2022-07-04', '2022-09-05', '2022-10-10', '2022-11-11', '2022-11-24', '2022-12-24', '2022-12-25',
            '2022-12-31'
        ]  # Liste der Feiertage

        holidays_str = ', '.join(f"'{h}'" for h in holidays)

        query = f"""
            SELECT OrderDate, storeID, TotalOrders
            FROM TopOrderDates
            WHERE OrderDate IN ({holidays_str})
            ORDER BY OrderDate, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch holiday order analysis data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /holiday_order_analysis endpoint: {e}")
        return jsonify({"error": "Error fetching holiday order analysis data"}), 500


@app.route('/avg_orders_per_hour', methods=['GET'])
def avg_orders_per_hour():
    """Endpunkt für die durchschnittlichen Bestellungen pro Stunde (angepasste Zeit)"""
    try:
        query = """
            SELECT Hour, storeID, AvgOrdersPerHour
            FROM AvgOrdersPerHour
            ORDER BY storeID, Hour;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average orders per hour data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /avg_orders_per_hour endpoint: {e}")
        return jsonify({"error": "Error fetching average orders per hour data"}), 500


@app.route('/avg_orders_per_hour_utc', methods=['GET'])
def avg_orders_per_hour_utc():
    """Endpunkt für die durchschnittlichen Bestellungen pro Stunde (UTC-Zeit)"""
    try:
        query = """
            SELECT Hour, storeID, AvgOrdersPerHour
            FROM AvgOrdersPerHourUTC
            ORDER BY storeID, Hour;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average orders per hour (UTC) data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /avg_orders_per_hour_utc endpoint: {e}")
        return jsonify({"error": "Error fetching average orders per hour (UTC) data"}), 500


@app.route('/store_sales_comparison', methods=['GET'])
def store_sales_comparison():
    """Endpunkt für den Verkaufsvergleich zwischen Stores"""
    try:
        query = """
            SELECT ProductName, storeID, SUM(Quantity) AS TotalQuantity
            FROM daily_store_pizza_sales
            GROUP BY ProductName, storeID
            ORDER BY ProductName, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store sales comparison data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_sales_comparison endpoint: {e}")
        return jsonify({"error": "Error fetching store sales comparison data"}), 500


@app.route('/store_sales_comparison_weekly', methods=['GET'])
def store_sales_comparison_weekly():
    """Endpunkt für den wöchentlichen Verkaufsvergleich zwischen Stores"""
    try:
        query = """
            SELECT yearWeek, PizzaName, storeID, SUM(Quantity) AS TotalQuantity
            FROM weekly_store_pizza_sales
            GROUP BY yearWeek, PizzaName, storeID
            ORDER BY yearWeek, PizzaName, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store sales comparison weekly data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_sales_comparison_weekly endpoint: {e}")
        return jsonify({"error": "Error fetching store sales comparison weekly data"}), 500


# customer analyse
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


# product analyse
@app.route('/most_popular_products', methods=['GET'])
def most_popular_products():
    """Endpunkt für die beliebtesten Produkte, nach name und kategorie möglich"""
    try:
        query = """
            SELECT ProductName, Category, Frequency
            FROM product_order_frequency
            ORDER BY Frequency DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch most popular products data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /most_popular_products endpoint: {e}")
        return jsonify({"error": "Error fetching most popular products data"}), 500


@app.route('/category_order_share', methods=['GET'])
def category_order_share():
    """Endpunkt für den Anteil jeder Kategorie an Anzahl der gesamten Bestellungen -> Kreisdiagramm"""
    try:
        query = """
            SELECT Category, SUM(Frequency) AS TotalFrequency,
                   ROUND(100.0 * SUM(Frequency) / (SELECT SUM(Frequency) FROM product_order_frequency), 2) AS Percentage
            FROM product_order_frequency
            GROUP BY Category
            ORDER BY TotalFrequency DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch category order share data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /category_order_share endpoint: {e}")
        return jsonify({"error": "Error fetching category order share data"}), 500


@app.route('/product_order_share', methods=['GET'])
def product_order_share():
    """Endpunkt für den Anteil jedes Produktnamens an Anzahl der gesamten Bestellungen -> Kreisdiagramm"""
    try:
        query = """
                SELECT 
                    ProductName, 
                    Category, 
                    Frequency,
                    ROUND(100.0 * Frequency / (SELECT SUM(Frequency) FROM product_order_frequency), 2) AS Percentage
                FROM product_order_frequency
                ORDER BY Percentage DESC;
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch product order share data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /product_order_share endpoint: {e}")
        return jsonify({"error": "Error fetching product order share data"}), 500


@app.route('/total_sales_per_category', methods=['GET'])
def total_sales_per_category():
    """Endpunkt für die Gesamtverkäufe pro Kategorie"""
    try:
        query = """
            SELECT Category, SUM(NumberOfPizzasSold) AS TotalPizzasSold
            FROM PizzaSalesSummary
            GROUP BY Category
            ORDER BY Category;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch total sales per category data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /total_sales_per_category endpoint: {e}")
        return jsonify({"error": "Error fetching total sales per category data"}), 500


@app.route('/weekly_sales_distribution', methods=['GET'])
def weekly_sales_distribution():
    """Endpunkt für die tägliche Verkaufsverteilung pro Produkt"""
    try:
        query = """
            SELECT DAYOFWEEK(orderDate) AS Weekday, ProductName, SUM(Quantity) AS TotalQuantity
            FROM daily_store_pizza_sales
            GROUP BY Weekday, ProductName
            ORDER BY Weekday, ProductName;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch weekly sales distribution data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_sales_distribution endpoint: {e}")
        return jsonify({"error": "Error fetching weekly sales distribution data"}), 500


@app.route('/sales_trend_by_size', methods=['GET'])
def sales_trend_by_size():
    """Endpunkt für Verkaufstrends nach Größe """  # vllt extra tabelle erstellen wenns zu lange dauert
    try:
        query = """
            SELECT orderDate, Size, SUM(Quantity) AS TotalQuantity
            FROM daily_store_pizza_sales_with_size
            GROUP BY orderDate, Size
            ORDER BY orderDate, Size;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch sales trend by size data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /sales_trend_by_size endpoint: {e}")
        return jsonify({"error": "Error fetching sales trend by size data"}), 500


@app.route('/size_popularity', methods=['GET'])
def size_popularity():
    """Endpunkt für die Beliebtheit von Pizzagrößen"""
    try:
        query = """
            SELECT Size, SUM(Quantity) AS TotalQuantity
            FROM daily_store_pizza_sales_with_size
            GROUP BY Size
            ORDER BY TotalQuantity DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch size popularity data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /size_popularity endpoint: {e}")
        return jsonify({"error": "Error fetching size popularity data"}), 500


@app.route('/popular_pizza_by_week', methods=['GET'])
def popular_pizza_by_week():
    """Endpunkt für die beliebtesten Pizza-Sorten pro Woche"""
    try:
        query = """
            SELECT yearWeek, PizzaName, SUM(Quantity) AS TotalQuantity
            FROM weekly_store_pizza_sales
            GROUP BY yearWeek, PizzaName
            ORDER BY yearWeek, TotalQuantity DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch popular pizza by week data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /popular_pizza_by_week endpoint: {e}")
        return jsonify({"error": "Error fetching popular pizza by week data"}), 500


@app.route('/total_profit_per_pizza', methods=['GET'])
def total_profit_per_pizza():
    """Endpunkt für den Gesamtprofit pro Pizza"""
    try:
        query = """
            SELECT SKU, Name, Size, Price, production_cost, profit
            FROM pizza_profit_analysis
            ORDER BY profit DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch total profit per pizza data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /total_profit_per_pizza endpoint: {e}")
        return jsonify({"error": "Error fetching total profit per pizza data"}), 500


@app.route('/cost_structure_per_pizza', methods=['GET'])
def cost_structure_per_pizza():
    """Endpunkt für die Kostenstruktur pro Pizza"""
    try:
        query = """
            SELECT SKU, Name, Size, Price, production_cost, 
                   ROUND(production_cost / Price * 100, 2) AS CostPercentage
            FROM pizza_profit_analysis
            ORDER BY SKU, Size;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch cost structure per pizza data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /cost_structure_per_pizza endpoint: {e}")
        return jsonify({"error": "Error fetching cost structure per pizza data"}), 500


@app.route('/margin_analysis', methods=['GET'])
def margin_analysis():
    """Endpunkt für die Margenanalyse pro Pizza"""
    try:
        query = """
            SELECT SKU, Name, Size, Price, production_cost, 
                   ROUND((Price - production_cost) / Price * 100, 2) AS ProfitMargin
            FROM pizza_profit_analysis
            ORDER BY ProfitMargin DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch margin analysis data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /margin_analysis endpoint: {e}")
        return jsonify({"error": "Error fetching margin analysis data"}), 500


@app.route('/size_cost_efficiency', methods=['GET'])
def size_cost_efficiency():
    """Endpunkt für die Kosteneffizienz der Pizzagrößen"""
    try:
        query = """
            SELECT SKU, Name, Size, Price, production_cost, 
                   ROUND(profit / production_cost, 2) AS CostEfficiency
            FROM pizza_profit_analysis
            ORDER BY SKU, Size;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch size cost efficiency data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /size_cost_efficiency endpoint: {e}")
        return jsonify({"error": "Error fetching size cost efficiency data"}), 500


if __name__ == '__main__':
    app.run(port=8080, debug=True)
