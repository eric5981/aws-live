from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *
from datetime import datetime

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route("/", methods=['GET', 'POST'])  #start page because got /
def home():
    return render_template('AddEmployee.html')

#@app.route("/", methods=['GET', 'POST'])  backup
#def home():
#    return render_template('AddEmp.html')


@app.route("/about", methods=['GET', 'POST'])
def about():
    return render_template('AboutUs.html', about=about)


@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    salary = request.form['salary']
    emp_image_file = request.files['emp_image_file']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location, salary))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddEmpOutput.html', name=emp_name)

@app.route("/getemp", methods=['GET', 'POST'])
def GetEmp():
    return render_template('GetEmployee.html') 

@app.route("/payroll", methods=['GET', 'POST'])
def Payroll():
    return render_template('EmployeePayroll.html') 

@app.route("/fetchinfo", methods=['GET', 'POST'])
def FetchInfo():
    try:
        emp_id = request.form['emp_id']
        cursor = db_conn.cursor()

        fetch_info_sql = "SELECT * FROM employee WHERE emp_id = %s"
        cursor.execute(fetch_info_sql,(emp_id))
        emp = cursor.fetchall()

        (id, fname, lname, priskill, location, salary) = emp[0]
        image_url = show_image(custombucket)
        #return render_template('GetEmpOutput.html',id=id,fname=fname,lname=lname,skill=priskill,location=location,salary=salary,image_url=image_url)
        return render_template('GetEmployeeOutput.html',id=id,fname=fname,lname=lname,skill=priskill,location=location,salary=salary,image_url=image_url)
    except Exception as e:
        return str(e)

def show_image(bucket):
    s3_client = boto3.client('s3')
    public_urls = []

    #check whether the emp_id inside the image_url
    emp_id = request.form['emp_id']
    try:
        for item in s3_client.list_objects(Bucket=bucket)['Contents']:
            presigned_url = s3_client.generate_presigned_url('get_object', Params = {'Bucket': bucket, 'Key': item['Key']}, ExpiresIn = 100)
            if emp_id in presigned_url:
                public_urls.append(presigned_url)
    except Exception as e:
       pass
   # print("[INFO] : The contents inside show_image = ", public_urls)
    return public_urls

@app.route("/attendance", methods=['GET', 'POST'])
def Attendance():
    id = request.form['emp_id']
    cursor = db_conn.cursor()
    fetch_info_sql = "SELECT first_name, last_name FROM employee WHERE emp_id = %s"
    cursor.execute(fetch_info_sql,(id))
    emp = cursor.fetchall()
    (fname, lname) = emp[0]
    emp_name = "" + fname + " " + lname
    return render_template('Attendance.html',id=id,emp_name=emp_name)

@app.route("/takeattendance", methods=['GET', 'POST'])
def TakeAttendance():
    now = datetime.now()
    dt_string = now.strftime("%d%m%Y%H%M%S")

    attendance = request.form.getlist('attendance')
    emp_id = request.form['emp_id']
    att_id = emp_id + dt_string
    insert_att_sql = 'INSERT INTO attendance VALUES (%s,%s,%s,%s)'
    cursor = db_conn.cursor()
    cursor.execute(insert_att_sql, (att_id,dt_string,attendance,emp_id))
    db_conn.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
