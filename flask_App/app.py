from flask import Flask, render_template, request
from flask import jsonify
from markupsafe import Markup
import duckdb
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

app = Flask(__name__)


# Helper: format DataFrame into an HTML table with numeric and percent formatting
def df_to_formatted_html(df: pd.DataFrame) -> str:
  if df is None or df.empty:
    return '<div class="text-muted">No data</div>'
  df2 = df.copy()
  for col in df2.columns:
    try:
      # numeric columns (integers / floats)
      if pd.api.types.is_numeric_dtype(df2[col]):
        # choose integer or float formatting depending on presence of fractional parts
        if (df2[col].dropna().apply(float).apply(float.is_integer).all() if len(df2[col].dropna())>0 else True):
          df2[col] = df2[col].apply(lambda x: f"{int(x):,}" if pd.notnull(x) else "")
        else:
          df2[col] = df2[col].apply(lambda x: f"{float(x):, .2f}".replace(' ,','') if pd.notnull(x) else "")
      else:
        # detect rate-like columns by name and format as percent
        lowered = col.lower()
        if any(k in lowered for k in ('rate','reorder','pct','percent')):
          def fmt_pct(x):
            if pd.isnull(x):
              return ''
            try:
              n = float(x)
              if abs(n) <= 1:
                return f"{n*100:.1f}%"
              return f"{n:.1f}%"
            except Exception:
              return str(x)
          df2[col] = df2[col].apply(fmt_pct)
        else:
          # coerce to string to avoid mixed types in HTML rendering
          df2[col] = df2[col].astype(str).fillna('')
    except Exception:
      # fallback: stringify the column
      df2[col] = df2[col].astype(str).fillna('')

  # use Bootstrap table classes and our data-table class
  return df2.to_html(classes='table table-sm table-striped data-table', index=False, escape=False)


# Path to DuckDB database used in the notebook; adjust via environment variable if needed
# Accept either `FINAL_INSTACART_DB` or `INSTACART_DB` environment variables. If not provided,
# fall back to the default location one level up from `flask_app`.
_env_db = os.getenv('FINAL_INSTACART_DB') or os.getenv('INSTACART_DB')
if _env_db:
  DB_PATH = os.path.expanduser(_env_db)
else:
  DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'final_instacart.db')

# Create a reusable connection function
def get_con():
    # if DB_PATH file exists use it, else default to in-memory
  if os.path.exists(DB_PATH):
    return duckdb.connect(database=DB_PATH)
  return duckdb.connect(database=':memory:')

@app.route('/')
def index():
    # Render the general introduction dashboard as the main page
    return general_dashboard()


@app.route('/general_dashboard')
def general_dashboard():
    con = get_con()
    # Q1
    q1 = """
    SELECT
      p.product_name, d.department, COUNT(*) AS total_items,
      AVG(CASE WHEN f.reordered = 1 THEN 1.0 ELSE 0.0 END) AS reorder_rate
    FROM fact_order_products f
    JOIN dim_product p    ON f.product_id = p.product_id
    JOIN dim_department d ON p.department_id = d.department_id
    GROUP BY p.product_name, d.department
    HAVING COUNT(*) > 100
    ORDER BY reorder_rate DESC, total_items DESC
    LIMIT 100;
    """
    q1_df = con.execute(q1).fetchdf()

    # Q2 day and hour
    q2_day = """
    SELECT 
      o.order_dow AS day_of_week,
      CASE 
        WHEN o.order_dow = 0 THEN 'Sunday'
        WHEN o.order_dow = 1 THEN 'Monday'
        WHEN o.order_dow = 2 THEN 'Tuesday'
        WHEN o.order_dow = 3 THEN 'Wednesday'
        WHEN o.order_dow = 4 THEN 'Thursday'
        WHEN o.order_dow = 5 THEN 'Friday'
        WHEN o.order_dow = 6 THEN 'Saturday'
      END AS day_name,
      COUNT(*) AS total_items
    FROM fact_order_products f
    JOIN dim_order o 
      ON f.order_id = o.order_id
    GROUP BY o.order_dow
    ORDER BY o.order_dow;
    """
    q2_hour = """
    SELECT
      o.order_hour_of_day AS hour_of_day,
      COUNT(*) AS total_items
    FROM fact_order_products f
    JOIN dim_order o ON f.order_id = o.order_id
    GROUP BY o.order_hour_of_day
    ORDER BY o.order_hour_of_day;
    """
    q2_day_df = con.execute(q2_day).fetchdf()
    q2_hour_df = con.execute(q2_hour).fetchdf()

    # Q3
    q3 = """
    WITH top_products AS (
      SELECT product_id, COUNT(*) AS total_items
      FROM fact_order_products
      GROUP BY product_id
      ORDER BY total_items DESC
      LIMIT 100
    ), filtered AS (
      SELECT f.order_id, f.product_id
      FROM fact_order_products f
      JOIN top_products t USING (product_id)
    )
    SELECT p1.product_name AS product_A, p2.product_name AS product_B, COUNT(*) AS times_bought_together
    FROM filtered f1
    JOIN filtered f2
      ON f1.order_id = f2.order_id AND f1.product_id < f2.product_id
    JOIN dim_product p1 ON f1.product_id = p1.product_id
    JOIN dim_product p2 ON f2.product_id = p2.product_id
    GROUP BY product_A, product_B
    ORDER BY times_bought_together DESC
    LIMIT 20;
    """
    q3_df = con.execute(q3).fetchdf()

    # Q4
    q4 = """
    WITH customer_stats AS (
      SELECT user_id, AVG(days_since_prior_order) AS avg_days_between_orders, COUNT(order_id) AS total_orders
      FROM dim_order
      WHERE days_since_prior_order IS NOT NULL
      GROUP BY user_id
    ), segments AS (
      SELECT user_id, avg_days_between_orders, total_orders,
        CASE WHEN avg_days_between_orders <= 7 THEN 'High-frequency'
             WHEN avg_days_between_orders BETWEEN 8 AND 20 THEN 'Medium-frequency'
             ELSE 'Low-frequency' END AS customer_segment
      FROM customer_stats
    )
    SELECT s.customer_segment, COUNT(DISTINCT s.user_id) AS num_customers, AVG(f.reordered) AS avg_reorder_rate
    FROM segments s
    JOIN dim_order o ON o.user_id = s.user_id
    JOIN fact_order_products f ON f.order_id = o.order_id
    GROUP BY s.customer_segment
    ORDER BY avg_reorder_rate DESC;
    """
    q4_df = con.execute(q4).fetchdf()

    con.close()

    # Build Plotly figures for each panel and return embedded HTML fragments
    figs = {}
    # Q1: top 10 products by reorder_rate
    if not q1_df.empty:
        q1_plot = q1_df.sort_values('reorder_rate', ascending=False).head(10)
        fig1 = px.bar(q1_plot, x='reorder_rate', y='product_name', orientation='h', color='department', title='Top 10 products by repeat purchase rate')
        figs['q1'] = pio.to_html(fig1, full_html=False, include_plotlyjs=False)
    else:
        figs['q1'] = '<div class="alert alert-warning">No data for Q1</div>'

    # Q2 day
    if not q2_day_df.empty:
        fig2d = px.bar(q2_day_df, x='day_name', y='total_items', title='Ordering activity by day of week')
        figs['q2_day'] = pio.to_html(fig2d, full_html=False, include_plotlyjs=False)
    else:
        figs['q2_day'] = '<div class="alert alert-warning">No data for Q2 (day)</div>'

    # Q2 hour
    if not q2_hour_df.empty:
        fig2h = px.line(q2_hour_df, x='hour_of_day', y='total_items', title='Ordering activity by hour of day')
        figs['q2_hour'] = pio.to_html(fig2h, full_html=False, include_plotlyjs=False)
    else:
        figs['q2_hour'] = '<div class="alert alert-warning">No data for Q2 (hour)</div>'

    # Q3
    if not q3_df.empty:
        q3_plot = q3_df.head(20)
        q3_plot['pair'] = q3_plot['product_A'] + ' + ' + q3_plot['product_B']
        fig3 = px.bar(q3_plot.iloc[::-1], x='times_bought_together', y='pair', orientation='h', title='Top product pairs bought together')
        figs['q3'] = pio.to_html(fig3, full_html=False, include_plotlyjs=False)
    else:
        figs['q3'] = '<div class="alert alert-warning">No data for Q3</div>'

    # Q4
    if not q4_df.empty:
        import plotly.graph_objects as go
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=q4_df['customer_segment'], y=q4_df['avg_reorder_rate'], name='Avg reorder rate', marker_color='skyblue', yaxis='y1'))
        fig4.add_trace(go.Scatter(x=q4_df['customer_segment'], y=q4_df['num_customers'], name='Number of customers', marker_color='blue', yaxis='y2'))
        fig4.update_layout(title='Reorder rate and number of customers by segment', yaxis=dict(title='Avg reorder rate'), yaxis2=dict(title='Number of customers', overlaying='y', side='right'))
        figs['q4'] = pio.to_html(fig4, full_html=False, include_plotlyjs=False)
    else:
        figs['q4'] = '<div class="alert alert-warning">No data for Q4</div>'

    return render_template('general_dashboard.html', plots=figs)

@app.route('/q1')
def q1():
    con = get_con()
    qry = """
    WITH product_stats AS (
      SELECT p.product_name, d.department,
             COUNT(*) AS total_orders,
             SUM(op.reordered) AS total_reorders,
             SUM(op.reordered)::DOUBLE / NULLIF(COUNT(*),0) AS reorder_rate
      FROM fact_order_products op
      JOIN dim_product p ON op.product_id = p.product_id
      JOIN dim_department d ON p.department_id = d.department_id
      GROUP BY 1,2
      HAVING COUNT(*) >= 50
    )
    SELECT product_name, department, reorder_rate, total_orders
    FROM product_stats
    ORDER BY reorder_rate DESC
    LIMIT 20;
    """
    df = con.execute(qry).fetchdf()
    con.close()
    if df.empty:
      table_html = 'No data found. Load DuckDB DB first.'
      plot_html = ''
    else:
      fig = px.bar(df.sort_values('reorder_rate', ascending=False).head(15),
             x='reorder_rate', y='product_name', orientation='h',
             labels={'reorder_rate':'Reorder rate','product_name':'Product'}, title='Top products by reorder rate')
      plot_html = pio.to_html(fig, full_html=False)
      table_html = df_to_formatted_html(df)

    # determine partial rendering (fragment) by query param `partial=1` or `true`
    partial = str(request.args.get('partial', '')).lower() in ('1', 'true', 'yes')
    return render_template('q1.html', plot_div=Markup(plot_html), table_html=Markup(table_html), partial=partial)

@app.route('/q2')
def q2():
    con = get_con()
    qry = """
    SELECT order_dow, order_hour_of_day, COUNT(*) AS orders
    FROM dim_order
    GROUP BY 1,2
    ORDER BY orders DESC
    LIMIT 100;
    """
    df = con.execute(qry).fetchdf()
    con.close()
    if df.empty:
      table_html = 'No data found. Load DuckDB DB first.'
      plot_html = ''
    else:
      fig = px.density_heatmap(df, x='order_hour_of_day', y='order_dow', z='orders', nbinsx=24, nbinsy=7,
                   title='Orders: hour of day vs day of week', labels={'order_hour_of_day':'Hour','order_dow':'Day of week'})
      plot_html = pio.to_html(fig, full_html=False)
      table_html = df_to_formatted_html(df)

    partial = str(request.args.get('partial', '')).lower() in ('1', 'true', 'yes')
    return render_template('q2.html', plot_div=Markup(plot_html), table_html=Markup(table_html), partial=partial)

@app.route('/q3')
def q3():
    con = get_con()
    qry = """
    WITH pairs AS (
      SELECT LEAST(p1.product_name, p2.product_name) AS product_a,
             GREATEST(p1.product_name, p2.product_name) AS product_b,
             COUNT(*) AS pair_count
      FROM fact_order_products op1
      JOIN fact_order_products op2
        ON op1.order_id = op2.order_id
       AND op1.product_id < op2.product_id
      JOIN dim_product p1 ON op1.product_id = p1.product_id
      JOIN dim_product p2 ON op2.product_id = p2.product_id
      GROUP BY 1,2
    )
    SELECT *
    FROM pairs
    ORDER BY pair_count DESC
    LIMIT 50;
    """
    df = con.execute(qry).fetchdf()
    con.close()
    if df.empty:
      table_html = 'No data found. Load DuckDB DB first.'
      plot_html = ''
    else:
      table_html = df_to_formatted_html(df)
      # create a bar chart for top pairs
      df['pair'] = df['product_a'] + ' | ' + df['product_b']
      fig = px.bar(df.head(20).iloc[::-1], x='pair', y='pair_count', orientation='v', title='Top co-purchased product pairs')
      fig.update_layout(xaxis={'tickangle':45})
      plot_html = pio.to_html(fig, full_html=False)

    partial = str(request.args.get('partial', '')).lower() in ('1', 'true', 'yes')
    return render_template('q3.html', plot_div=Markup(plot_html), table_html=Markup(table_html), partial=partial)

@app.route('/q4')
def q4():
    con = get_con()
    qry = """
    WITH order_sizes AS (
      SELECT o.user_id, o.order_id, COUNT(*) AS basket_size
      FROM dim_order o
      JOIN fact_order_products op ON o.order_id = op.order_id
      GROUP BY 1,2
    ),
    user_segments AS (
      SELECT user_id, AVG(basket_size) AS avg_basket,
             CASE WHEN AVG(basket_size) < 8 THEN 'small'
                  WHEN AVG(basket_size) BETWEEN 8 AND 15 THEN 'medium'
                  ELSE 'large' END AS segment
      FROM order_sizes
      GROUP BY 1
    ),
    user_reorder AS (
      SELECT u.segment, COUNT(*) AS total_items, SUM(op.reordered) AS total_reorders,
             SUM(op.reordered)::DOUBLE / NULLIF(COUNT(*),0) AS reorder_rate
      FROM user_segments u
      JOIN dim_order o ON u.user_id = o.user_id
      JOIN fact_order_products op ON o.order_id = op.order_id
      GROUP BY 1
    )
    SELECT * FROM user_reorder ORDER BY segment;
    """
    df = con.execute(qry).fetchdf()
    con.close()
    if df.empty:
      table_html = 'No data found. Load DuckDB DB first.'
      plot_html = ''
    else:
      fig = px.bar(df, x='segment', y='reorder_rate', title='Reorder rate by customer segment')
      plot_html = pio.to_html(fig, full_html=False)
      table_html = df_to_formatted_html(df)

    partial = str(request.args.get('partial', '')).lower() in ('1', 'true', 'yes')
    return render_template('q4.html', plot_div=Markup(plot_html), table_html=Markup(table_html), partial=partial)

@app.route('/q5')
def q5():
    con = get_con()
    qry = """
    WITH recency AS (
      SELECT user_id, order_id, order_number, days_since_prior_order
      FROM dim_order
      WHERE days_since_prior_order IS NOT NULL
    ),
    summary AS (
      SELECT AVG(days_since_prior_order) AS avg_days, MEDIAN(days_since_prior_order) AS median_days FROM recency
    ),
    by_dow AS (
      SELECT order_dow, AVG(days_since_prior_order) AS avg_days FROM dim_order WHERE days_since_prior_order IS NOT NULL GROUP BY order_dow
    ),
    by_hour AS (
      SELECT order_hour_of_day, AVG(days_since_prior_order) AS avg_days FROM dim_order WHERE days_since_prior_order IS NOT NULL GROUP BY order_hour_of_day
    )
    SELECT 'overall' AS slice, * FROM summary
    UNION ALL
    SELECT 'by_dow:' || order_dow AS slice, avg_days AS avg_days, NULL AS median_days FROM by_dow
    UNION ALL
    SELECT 'by_hour:' || order_hour_of_day AS slice, avg_days AS avg_days, NULL AS median_days FROM by_hour
    ORDER BY slice;
    """
    df = con.execute(qry).fetchdf()
    con.close()
    if df.empty:
      table_html = 'No data found. Load DuckDB DB first.'
    else:
      table_html = df_to_formatted_html(df)

    partial = str(request.args.get('partial', '')).lower() in ('1', 'true', 'yes')
    return render_template('q5.html', table_html=Markup(table_html), partial=partial)


# --- JSON API endpoints for client-side rendering ---
@app.route('/api/q1')
def api_q1():
    con = get_con()
    # Q1: Customer loyalty and product performance
    # Which products and departments show the highest rates of repeat purchases?
    qry = """
    SELECT
      p.product_id, p.product_name, d.department, a.aisle, COUNT(*) AS total_items,
      AVG(CASE WHEN f.reordered = 1 THEN 1.0 ELSE 0.0 END) AS reorder_rate
    FROM fact_order_products f
    JOIN dim_product p    ON f.product_id = p.product_id
    JOIN dim_department d ON p.department_id = d.department_id
    JOIN dim_aisles a ON a.aisle_id = p.aisle_id
    GROUP BY p.product_id, p.product_name, d.department, a.aisle
    HAVING COUNT(*) > 100
    ORDER BY reorder_rate DESC, total_items DESC
    LIMIT 20;
    """
    df = con.execute(qry).fetchdf()
    con.close()
    return jsonify(columns=df.columns.tolist(), records=df.fillna('').to_dict(orient='records'))


@app.route('/api/q2')
def api_q2():
    con = get_con()
    # Q2: Demand over time and staff scheduling
    # Day-level aggregation
    qry_day = """
    SELECT 
      o.order_dow AS day_of_week,
      CASE 
        WHEN o.order_dow = 0 THEN 'Sunday'
        WHEN o.order_dow = 1 THEN 'Monday'
        WHEN o.order_dow = 2 THEN 'Tuesday'
        WHEN o.order_dow = 3 THEN 'Wednesday'
        WHEN o.order_dow = 4 THEN 'Thursday'
        WHEN o.order_dow = 5 THEN 'Friday'
        WHEN o.order_dow = 6 THEN 'Saturday'
      END AS day_name,
      COUNT(*) AS total_items
    FROM fact_order_products f
    JOIN dim_order o 
      ON f.order_id = o.order_id
    GROUP BY o.order_dow
    ORDER BY o.order_dow;
    """

    # Hour-level aggregation
    qry_hour = """
    SELECT
      o.order_hour_of_day AS hour_of_day,
      COUNT(*) AS total_items
    FROM fact_order_products f
    JOIN dim_order o ON f.order_id = o.order_id
    GROUP BY o.order_hour_of_day
    ORDER BY o.order_hour_of_day;
    """

    df_day = con.execute(qry_day).fetchdf()
    df_hour = con.execute(qry_hour).fetchdf()
    con.close()
    # return both day and hour data together
    return jsonify(day_columns=df_day.columns.tolist(), day_records=df_day.fillna(0).to_dict(orient='records'),
                   hour_columns=df_hour.columns.tolist(), hour_records=df_hour.fillna(0).to_dict(orient='records'))


@app.route('/api/q3')
def api_q3():
    con = get_con()
    # Q3: Products that are purchased together (cross-selling)
    qry = """
    WITH top_products AS (
      SELECT
        product_id,
        COUNT(*) AS total_items
      FROM fact_order_products
      GROUP BY product_id
      ORDER BY total_items DESC
      LIMIT 100
    ),
    filtered AS (
      SELECT
        f.order_id,
        f.product_id
      FROM fact_order_products f
      JOIN top_products t USING (product_id)
    )
    SELECT
      p1.product_name AS product_A,
      p2.product_name AS product_B,
      COUNT(*) AS times_bought_together
    FROM filtered f1
    JOIN filtered f2
        ON f1.order_id = f2.order_id
       AND f1.product_id < f2.product_id
    JOIN dim_product p1 ON f1.product_id = p1.product_id
    JOIN dim_product p2 ON f2.product_id = p2.product_id
    GROUP BY product_A, product_B
    ORDER BY times_bought_together DESC
    LIMIT 20;
    """
    df = con.execute(qry).fetchdf()
    con.close()
    return jsonify(columns=df.columns.tolist(), records=df.fillna('').to_dict(orient='records'))


@app.route('/api/q4')
def api_q4():
    con = get_con()
    # Q4: Customer segments and repurchase behavior
    qry = """
    WITH customer_stats AS (
      SELECT user_id, AVG(days_since_prior_order) AS avg_days_between_orders, COUNT(order_id) AS total_orders
      FROM dim_order
      WHERE days_since_prior_order IS NOT NULL
      GROUP BY user_id
    ),
    segments AS (
      SELECT
        user_id, avg_days_between_orders, total_orders,
        CASE
          WHEN avg_days_between_orders <= 7 THEN 'High-frequency'
          WHEN avg_days_between_orders BETWEEN 8 AND 20 THEN 'Medium-frequency'
          ELSE 'Low-frequency'
        END AS customer_segment
      FROM customer_stats
    )
    SELECT
      s.customer_segment, COUNT(DISTINCT s.user_id) AS num_customers, AVG(f.reordered) AS avg_reorder_rate,
      AVG(s.avg_days_between_orders) AS avg_days_between_orders
    FROM segments s
    JOIN dim_order o             ON o.user_id = s.user_id
    JOIN fact_order_products f   ON f.order_id = o.order_id
    GROUP BY s.customer_segment
    ORDER BY avg_reorder_rate DESC;
    """
    df = con.execute(qry).fetchdf()
    con.close()
    return jsonify(columns=df.columns.tolist(), records=df.fillna(0).to_dict(orient='records'))


@app.route('/api/q5')
def api_q5():
    con = get_con()
    qry = """
    WITH recency AS (
      SELECT user_id, order_id, order_number, days_since_prior_order
      FROM dim_order
      WHERE days_since_prior_order IS NOT NULL
    ),
    summary AS (
      SELECT AVG(days_since_prior_order) AS avg_days, MEDIAN(days_since_prior_order) AS median_days FROM recency
    ),
    by_dow AS (
      SELECT order_dow, AVG(days_since_prior_order) AS avg_days FROM dim_order WHERE days_since_prior_order IS NOT NULL GROUP BY order_dow
    ),
    by_hour AS (
      SELECT order_hour_of_day, AVG(days_since_prior_order) AS avg_days FROM dim_order WHERE days_since_prior_order IS NOT NULL GROUP BY order_hour_of_day
    )
    SELECT 'overall' AS slice, * FROM summary
    UNION ALL
    SELECT 'by_dow:' || order_dow AS slice, avg_days AS avg_days, NULL AS median_days FROM by_dow
    UNION ALL
    SELECT 'by_hour:' || order_hour_of_day AS slice, avg_days AS avg_days, NULL AS median_days FROM by_hour
    ORDER BY slice;
    """
    df = con.execute(qry).fetchdf()
    con.close()
    return jsonify(columns=df.columns.tolist(), records=df.fillna('').to_dict(orient='records'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)
