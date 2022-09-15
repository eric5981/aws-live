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

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s, %s,%s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location, salary,0))
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

#@app.route("/payroll", methods=['GET', 'POST'])
#def Payroll():
#    return render_template('EmployeePayroll.html') 

@app.route("/fetchinfo", methods=['GET', 'POST'])
def FetchInfo():
    try:
        emp_id = request.form['emp_id']
        cursor = db_conn.cursor()
        fetch_info_sql = "SELECT * FROM employee WHERE emp_id = %s"
        cursor.execute(fetch_info_sql,(emp_id))
        emp = cursor.fetchall()
        (id, fname, lname, priskill, location, salary, deduction) = emp[0]
        image_url = show_image(custombucket, emp_id)
        emp_netsalary = salary - deduction
        att_emp_sql = "SELECT date,time,status FROM attendance A, employee E WHERE E.emp_id = A.emp_id AND A.emp_id = %s AND date = %s"
        mycursor = db_conn.cursor()
        now = datetime.now()
        date_string = now.strftime("%d/%m/%Y")
        rows_count = mycursor.execute(att_emp_sql,(emp_id,date_string))
        if rows_count == 0:
            dt = "No"
            status = "Record"
        else:
            att_result = mycursor.fetchall()
            (date,time,status) = att_result[-1]
            dt = date + " " + time
        #return render_template('GetEmpOutput.html',id=id,fname=fname,lname=lname,skill=priskill,location=location,salary=salary,image_url=image_url)
        return render_template('GetEmployeeOutput.html',id=id,fname=fname,lname=lname,skill=priskill,location=location,emp_netsalary=emp_netsalary,image_url=image_url,dt=dt,status=status)
    except Exception as e:
            return str(e)

def show_image(bucket,emp_id):
    s3_client = boto3.client('s3')
    public_urls = []

    #check whether the emp_id inside the image_url
    emp_id = "1"
    try:
        for item in s3_client.list_objects(Bucket=bucket)['Contents']:
            presigned_url = s3_client.generate_presigned_url('get_object', Params = {'Bucket': bucket, 'Key': item['Key']}, ExpiresIn = 100)
            if emp_id in presigned_url:
                public_urls.append(presigned_url)
    except Exception as e:
       pass
    print("[INFO] : The contents inside show_image = ", public_urls)
    return public_urls

@app.route("/update", methods=['GET', 'POST'])
def Update():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    #emp_image_file = request.files['emp_image_file']
    update_sql = "UPDATE employee SET first_name = %s, last_name = %s, pri_skill = %s, location = %s WHERE emp_id = %s"
    cursor = db_conn.cursor()
    cursor.execute(update_sql, (first_name, last_name, pri_skill, location,emp_id))
    db_conn.commit()
    image_url = show_image(custombucket, emp_id)
    name = first_name + " " + last_name
    return render_template('UpdateOutput.html',id=emp_id,name=name)

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

@app.route("/takeattendance", methods=['GET', 'POST'])   #dunno is my issue ma, i try the attendance at 3am but it save time is 8 hours ago "14/09/2022 19:00:09 Absent"
def TakeAttendance():
    now = datetime.now()
    dt = now.strftime("%d%m%Y%H%M%S")
    date_string = now.strftime('%d/%m/%Y')
    time_string = now.strftime('%H:%M:%S')

    attendance = request.form.getlist('attendance')
    emp_id = request.form['emp_id']
    att_id = emp_id + dt
    date = request.form['date'] + date_string
    time = request.form['time'] + time_string
    insert_att_sql = 'INSERT INTO attendance VALUES (%s,%s,%s,%s,%s)'
    cursor = db_conn.cursor()
    cursor.execute(insert_att_sql, (att_id,date,time,attendance,emp_id))
    fetch_info_sql = "SELECT first_name, last_name FROM employee WHERE emp_id = %s"
    cursor.execute(fetch_info_sql,(emp_id))
    emp = cursor.fetchall()
    (fname, lname) = emp[0]
    emp_name = "" + fname + " " + lname
    db_conn.commit()
    return render_template('AttendanceOutput.html', id=emp_id,name=emp_name)

@app.route("/payroll", methods=['GET', 'POST'])
def Payroll():
    id = request.form['emp_id']
    cursor = db_conn.cursor()
    fetch_info_sql = "SELECT first_name, last_name, salary, deduction FROM employee WHERE emp_id = %s"
    cursor.execute(fetch_info_sql,(id))
    emp = cursor.fetchall()
    (fname, lname, esalary, ededuction) = emp[0]
    emp_name = "" + fname + " " + lname
    emp_salary = esalary
    emp_deduction = ededuction
    return render_template('EmployeePayroll.html',id=id,emp_name=emp_name,emp_salary=emp_salary,emp_deduction=emp_deduction)

@app.route("/payrollupdate", methods=['GET', 'POST'])
def PayrollUpdate():
    emp_id = request.form['emp_id']
    name = request.form['emp_name']
    salary = request.form['salary']
    deduction = request.form['deduction']
    update_sql = "UPDATE employee SET salary = %s, deduction = %s WHERE emp_id = %s"
    cursor = db_conn.cursor()
    cursor.execute(update_sql, (salary, deduction, emp_id))
    db_conn.commit()
    return render_template('UpdatePayrollOutput.html',id=emp_id,name=name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
