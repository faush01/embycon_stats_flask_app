
# A very simple Flask Hello World app for you to get started with...

from flask import Flask
from flask import request
from flask import render_template
from flask import redirect

import MySQLdb
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["DEBUG"] = True

@app.route('/')
def hello_world():
    return 'no data'

'''
DROP TABLE error_report;
CREATE TABLE error_report (
id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
time_stamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
ip VARCHAR(32),
data LONGTEXT,
PRIMARY KEY (`id`));
SELECT * FROM error_report;
'''

'''
DROP TABLE activity;
CREATE TABLE activity (
date_stamp DATE,
server_id VARCHAR(256),
activity_type VARCHAR(64),
count int);
SELECT * FROM activity;
'''

def save_activity(data):

    conn = MySQLdb.connect(host="allthedata.mysql.pythonanywhere-services.com",
                     user="allthedata",
                     passwd="***********",
                     db="allthedata$error_submissions")

    cursor = conn.cursor()

    server_id = data.get("server_id", None)
    if not server_id:
        return

    activity = data.get("activity", {})

    for activity_date in activity:

        try:
            tokens = activity_date.split('-')
            print("Tokens : " + str(tokens))
            data_date = datetime(int(tokens[0]), int(tokens[1]), int(tokens[2]))
            days_ago_14 = datetime.utcnow() - timedelta(days=14)
            days_ahead_3 = datetime.utcnow() + timedelta(days=3)
            new_activity_date = None
            if data_date < days_ago_14 or data_date > days_ahead_3:
                print("Data date not in valid range: " + str(activity_date) + " utcnow():" + str(datetime.utcnow()))
                utcnow = datetime.utcnow()
                new_activity_date = "%s-%s-%s" % (utcnow.year, utcnow.month, utcnow.day)
                print("New Activity Date: " + new_activity_date)
        except Exception as error:
            print("Error parsing date: " + str(error))

        activity_types = activity[activity_date]

        for activity_type in activity_types:
            if new_activity_date:
                activity_date = new_activity_date

            count = activity_types.get(activity_type, 0)

            sql = "SELECT * FROM activity WHERE date_stamp = %s AND server_id = %s AND activity_type = %s"
            cursor.execute(sql, (activity_date, server_id, activity_type))

            row = cursor.fetchone()
            if row:
                sql = "UPDATE activity SET count = count + %s WHERE date_stamp = %s AND server_id = %s AND activity_type = %s"
                cursor.execute(sql, (count, activity_date, server_id, activity_type))
            else:
                sql = "INSERT INTO activity (date_stamp, server_id, activity_type, count) values (%s, %s, %s, %s)"
                cursor.execute(sql, (activity_date, server_id, activity_type, count))

    conn.commit()
    conn.close()


@app.route('/version', methods=['GET', 'POST'])
def version_check():

    if request.json:
        submitted_data = request.json
        save_activity(submitted_data)

    return "{\"message\": \"OK\"}"


@app.route('/activity', methods=['GET'])
def activity():

    conn = MySQLdb.connect(host="allthedata.mysql.pythonanywhere-services.com",
                     user="allthedata",
                     passwd="*******",
                     db="allthedata$error_submissions")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT str_to_date(concat(yearweek(date_stamp), ' monday'), '%X%V %W') AS `date`,
        COUNT(DISTINCT(server_id)) AS servers
        FROM activity
        GROUP BY yearweek(date_stamp) ORDER BY yearweek(date_stamp)
        """)

    weekly_results = {}

    for row in cursor:
        if row[0] not in weekly_results:
            weekly_results[row[0]] = {}
        weekly_results[row[0]]["server"] = row[1]

    cursor.execute("""
        SELECT str_to_date(concat(yearweek(date_stamp), ' monday'), '%X%V %W') AS `date`,
        SUM(count) AS servers
        FROM activity
        GROUP BY yearweek(date_stamp) ORDER BY yearweek(date_stamp)
        """)

    for row in cursor:
        if row[0] not in weekly_results:
            weekly_results[row[0]] = {}
        weekly_results[row[0]]["play"] = row[1]

    cursor.execute("""
        SELECT date_stamp,
        SUM(count) AS play_count,
        COUNT(DISTINCT server_id) AS server_count
        FROM activity
        GROUP BY date_stamp
        ORDER BY date_stamp
        """)

    results_plays_daily = []
    for row in cursor:
        item = {}
        item["date"] = row[0]
        item["play_count"] = str(row[1])
        item["server_count"] = str(row[2])
        results_plays_daily.append(item)

    return render_template("activity.html",
                            plays_daily = results_plays_daily,
                            weekly_data = weekly_results)


@app.route('/submit', methods=['GET', 'POST'])
def submit_error():

    if request.json:
        submitted_data = request.json

        save_error_data(submitted_data)
        return "Submitted: %s" % submitted_data.get("event")

    else:
        return "no data"


@app.route('/show', methods=['GET'])
def show_error():

    reports = reports_data()
    return render_template("show_reports.html", reports = reports)


@app.route('/show_item/<int:item_id>', methods=['GET'])
def show_item(item_id):

    conn = MySQLdb.connect(host="allthedata.mysql.pythonanywhere-services.com",
                     user="allthedata",
                     passwd="*********",
                     db="allthedata$error_submissions")
    cursor = conn.cursor()
    cursor.execute("SELECT data FROM error_report WHERE id=%s", (item_id,))
    row = cursor.fetchone()

    item_data = {}
    if row is not None:
        item_data = json.loads(row[0])

    return render_template("show_item.html", item_data = item_data)


@app.route('/delete/<int:item_id>', methods=['GET', 'POST'])
def delete_item(item_id):

    conn = MySQLdb.connect(host="allthedata.mysql.pythonanywhere-services.com",
                     user="allthedata",
                     passwd="***********",
                     db="allthedata$error_submissions")

    cursor = conn.cursor()
    query = "DELETE FROM error_report WHERE id = %s"
    cursor.execute(query, (item_id,))
    conn.commit()

    return redirect("/show")


def save_error_data(data):

    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr

    conn = MySQLdb.connect(host="allthedata.mysql.pythonanywhere-services.com",
                     user="allthedata",
                     passwd="*********",
                     db="allthedata$error_submissions")

    data_json = json.dumps(data)
    ip_address = str(ip)
    cur = conn.cursor()
    cur.execute("INSERT INTO error_report (ip, data) VALUES (%s, %s)", (ip_address, data_json))
    conn.commit()


def reports_data():

    conn = MySQLdb.connect(host="allthedata.mysql.pythonanywhere-services.com",
                     user="allthedata",
                     passwd="*********",
                     db="allthedata$error_submissions")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM error_report ORDER BY time_stamp DESC LIMIT 20")

    reports = []

    for row in cursor:

        report_data = {}
        try:
            report_data = json.loads(row[3])
        except:
            pass

        item = {}
        item["id"] = str(row[0])
        item["log_time"] = str(row[1])
        item["ip"] = str(row[2])
        item["error_type"] = report_data.get("error_type", "")
        item["error_short"] = report_data.get("error_short", "")
        item["addon_version"] = report_data.get("addon_version", "")

        reports.append(item)

        '''
        error_stack = report_data.get("error_stack", [])
        stack_string = ""
        for line in error_stack:
            stack_string += line
        table_data += "<td><pre>" + stack_string + "</pre></td>\n"

        formatted_raw = json.dumps(report_data, indent=4, sort_keys=True)
        table_data += "<td><pre>" + formatted_raw + "</pre></td>\n"
        '''

    return reports


