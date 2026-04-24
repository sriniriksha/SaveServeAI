from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import random
import json
import os

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secret123"

# 🔐 Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

# 📂 File for persistence
DATA_FILE = "history.json"


# 🔄 LOAD HISTORY FROM FILE
def load_history():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []


# 💾 SAVE HISTORY TO FILE
def save_history(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


history = load_history()


# 🏨 FIRST PAGE
@app.route('/')
def start():
    return render_template('hotel.html')


# 🏨 SAVE HOTEL + CITY
@app.route('/set_hotel', methods=['POST'])
def set_hotel():
    session['hotel'] = request.form['hotel']
    session['city'] = request.form['city']
    return redirect('/home')


# 🏠 HOME
@app.route('/home')
def home():
    return render_template(
        'index.html',
        hotel=session.get('hotel'),
        city=session.get('city')
    )


# 🔐 LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin_form')
        return "Invalid credentials!"
    return render_template('login.html')


# 🚪 LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# 👨‍💼 ADMIN FORM
@app.route('/admin_form')
def admin_form():
    if not session.get('admin'):
        return redirect('/login')

    return render_template(
        'admin_form.html',
        hotel=session.get('hotel'),
        city=session.get('city')
    )


# 👤 STAFF PAGE
@app.route('/user')
def user():
    return render_template(
        'user.html',
        hotel=session.get('hotel'),
        city=session.get('city')
    )


# 👤 STAFF PREDICTION
@app.route('/predict_user', methods=['POST'])
def predict_user():
    try:
        food = int(request.form['food'])
        people = int(request.form['people'])

        leftover = max(0, food - people)

        return render_template(
            'user_result.html',
            leftover=leftover,
            hotel=session.get('hotel'),
            city=session.get('city')
        )
    except:
        return "Error in input"


# 👨‍💼 ADMIN PREDICTION (FINAL FIXED LOGIC)
@app.route('/predict', methods=['POST'])
def predict():
    global history

    try:
        days = int(request.form['days'])

        total_leftover = 0
        total_prepared = 0
        categories = []

        avg_map = {
            "meal": 1,
            "seafood": 0.9,
            "frozen": 0.6,
            "pasta": 0.85,
            "bakery": 0.8,
            "bbq": 1.1,
            "dessert": 0.4,
            "beverages": 0.7,
            "vegan": 0.8
        }

        # 🔁 MULTI CATEGORY LOOP
        for i in range(1, 7):
            food = request.form.get(f'food{i}')
            people = request.form.get(f'people{i}')
            food_type = request.form.get(f'type{i}')

            if food and people and food_type:
                food = int(food)
                people = int(people)

                total_prepared += food
                avg = avg_map.get(food_type, 1)

                # ✅ FIXED TOTAL CONSUMPTION
                fluctuation = random.uniform(0.9, 1.1)
                total_consumed = people * avg * days * fluctuation

                cat_waste = max(0, int(food - total_consumed))
                total_leftover += cat_waste

                categories.append({
                    "type": food_type,
                    "prepared": food,
                    "served": people,
                    "waste": cat_waste
                })

        avg_leftover = int(total_leftover / days) if days > 0 else 0

        # ✅ CORRECT WASTE %
        waste_percent = round((total_leftover / total_prepared) * 100, 2) if total_prepared > 0 else 0

        # 🌱 CARBON
        carbon_saved = round(total_leftover * 0.5, 2)

        # 🎯 PRIORITY
        if total_leftover > 100:
            priority = "Urgent 🚨"
        elif total_leftover > 50:
            priority = "High"
        elif total_leftover > 20:
            priority = "Medium"
        else:
            priority = "Low"

        current_time = datetime.now().strftime("%d-%m-%Y %H:%M")

        # 📂 SAVE HISTORY
        new_entry = {
            "time": current_time,
            "hotel": session.get('hotel'),
            "city": session.get('city'),
            "categories": categories,
            "waste": total_leftover,
            "percent": waste_percent,
            "priority": priority
        }

        history.append(new_entry)
        save_history(history)  # 💾 persist

        return render_template(
            'result.html',
            total_leftover=total_leftover,
            avg_leftover=avg_leftover,
            waste_percent=waste_percent,
            waste_level="Updated",
            carbon_saved=carbon_saved,
            time=current_time,
            priority=priority,
            hotel=session.get('hotel'),
            city=session.get('city'),
            categories=categories
        )

    except Exception as e:
        return str(e)


# 📂 HISTORY PAGE
@app.route('/history')
def view_history():
    if not session.get('admin'):
        return redirect('/login')
    return render_template('history.html', history=history)


# 📥 DOWNLOAD FULL PDF
@app.route('/download_report')
def download_report():
    if not session.get('admin'):
        return redirect('/login')

    doc = SimpleDocTemplate("report.pdf")
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("SaveServe AI - Full History Report", styles['Title']))
    elements.append(Spacer(1, 20))

    if not history:
        elements.append(Paragraph("No data available.", styles['Normal']))
    else:
        for idx, entry in enumerate(history, start=1):

            elements.append(Paragraph(f"Record {idx}", styles['Heading2']))
            elements.append(Spacer(1, 10))

            elements.append(Paragraph(f"Hotel: {entry.get('hotel', '')}", styles['Normal']))
            elements.append(Paragraph(f"City: {entry.get('city', '')}", styles['Normal']))
            elements.append(Paragraph(f"Date & Time: {entry.get('time', '')}", styles['Normal']))
            elements.append(Paragraph(f"Total Waste: {entry.get('waste', 0)} plates", styles['Normal']))
            elements.append(Paragraph(f"Waste Percentage: {entry.get('percent', 0)}%", styles['Normal']))
            elements.append(Paragraph(f"Priority: {entry.get('priority', '')}", styles['Normal']))

            # 🔥 CATEGORY BREAKDOWN
            if 'categories' in entry:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("Category Breakdown:", styles['Heading3']))

                for cat in entry['categories']:
                    elements.append(Paragraph(
                        f"{cat['type']} → Prepared: {cat['prepared']}, "
                        f"Served: {cat['served']}, Waste: {cat['waste']}",
                        styles['Normal']
                    ))

            elements.append(Spacer(1, 20))

    doc.build(elements)

    return "Full report downloaded! Check your project folder 📂"


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
