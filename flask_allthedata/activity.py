
import MySQLdb
import json
from datetime import datetime, timedelta

def save_activity(data):

    conn = MySQLdb.connect(host="allthedata.mysql.pythonanywhere-services.com",
                     user="allthedata",
                     passwd="*******",
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
            print(activity_date + " " + activity_type + " " + str(count))

            sql = "SELECT * FROM activity WHERE date_stamp = %s AND server_id = %s AND activity_type = %s"
            cursor.execute(sql, (activity_date, server_id, activity_type))

            row = cursor.fetchone()
            if row:
                print("Updating")
                sql = "UPDATE activity SET count = count + %s WHERE date_stamp = %s AND server_id = %s AND activity_type = %s"
                #cursor.execute(sql, (count, activity_date, server_id, activity_type))
            else:
                print("Adding")
                sql = "INSERT INTO activity (date_stamp, server_id, activity_type, count) values (%s, %s, %s, %s)"
                #cursor.execute(sql, (activity_date, server_id, activity_type, count))

    conn.commit()
    conn.close()



activity_data = """
{"server_id": "f3344813d4f54337b878362fe27d79e3", "version_emby": "3.2.70.0", "client_id": "58F25E66300E46F1A57EB483C8ED223D", "activity": {"2018-2-05": {"DirectStream": 1}, "2018-2-10": {"DirectStream": 5}}, "version_kodi": "17.6 Git:20171114-a9a7a20", "client_utc_date": "2018-2-14", "version_addon": "1.4.48"}
"""

data = json.loads(activity_data)

save_activity(data)

