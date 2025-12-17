from flask import Flask, send_file, render_template, jsonify
import pandas as pd
import os
import io

app = Flask(__name__)
CSV_FILE = 'owen_cloud_data.csv'

def get_data(limit=100):
    if not os.path.exists(CSV_FILE):
        return None
    
    try:
        # Читаем CSV, пропуская возможные битые строки
        df = pd.read_csv(CSV_FILE)
        
        # Если файл пустой
        if df.empty:
            return None
            
        # Берем последние limit строк
        df_tail = df.tail(limit)
        
        # Сортируем: новые сверху (для таблицы)
        df_display = df_tail.iloc[::-1]
        
        # Для графика нужны данные в хронологическом порядке
        df_chart = df_tail
        
        return {
            'table': df_display,
            'chart': df_chart
        }
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

@app.route('/')
def index():
    data = get_data(100)
    
    if data is None:
        return render_template('index.html', error="Файл данных пока не создан или пуст.")
    
    # Подготовка данных для таблицы
    columns = data['table'].columns.tolist()
    records = data['table'].to_dict('records')
    
    # Подготовка данных для графика (преобразуем в JSON-friendly формат)
    # Предполагаем, что datetime - это ось X, а остальные (кроме timestamp) - серии
    chart_data = {
        'labels': data['chart']['datetime'].tolist(),
        'datasets': []
    }
    
    # Пытаемся определить числовые колонки для графика
    # Исключаем timestamp и datetime
    numeric_cols = data['chart'].select_dtypes(include=['float64', 'int64']).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in ['timestamp']]
    
    # Если не нашли числовых (все строки?), пробуем все кроме времени
    if not numeric_cols:
         cols = data['chart'].columns.tolist()
         numeric_cols = [c for c in cols if c not in ['timestamp', 'datetime']]

    for col in numeric_cols:
        # Простая генерация цветов не помешала бы, но Chart.js может и сам, или зададим базовый набор
        chart_data['datasets'].append({
            'label': col,
            'data': data['chart'][col].tolist(),
            'borderWidth': 2,
            'tension': 0.4, # Сглаживание
            'pointRadius': 2
        })

    return render_template('index.html', 
                           columns=columns, 
                           records=records, 
                           chart_data=chart_data)

@app.route('/download')
def download():
    if not os.path.exists(CSV_FILE):
        return "Файл не найден", 404
    return send_file(CSV_FILE, as_attachment=True, download_name='owen_data.csv')

if __name__ == '__main__':
    # Запуск на всех интерфейсах, порт 5000
    app.run(host='0.0.0.0', port=5000, debug=False)
