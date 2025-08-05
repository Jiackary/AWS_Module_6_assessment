from flask import Flask, render_template_string, request, redirect, url_for
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, BooleanAttribute
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)

s3_client = boto3.client("s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    region_name=os.getenv("AWS_REGION"))

bucket = "assessment-mod-6-1701"

class todo(Model):
    class Meta:
        table_name = "todo"
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_session_token = os.getenv("AWS_SESSION_TOKEN")
        region_name = os.getenv("AWS_REGION")
    
    title = UnicodeAttribute(hash_key=True)
    id = NumberAttribute(range_key=True)
    complete = BooleanAttribute(default=False)

@app.route("/")
def home():
    try:
        if not todo.exists():
            print("Table doesn't exist, creating...")
            todo.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
            print("Table created successfully")
        
        todo_list = list(todo.scan())
        response = s3_client.get_object(Bucket=bucket, Key="base.html")
        html_template = response['Body'].read().decode('utf-8')
        return render_template_string(html_template, todo_list=todo_list)
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500

@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title")
    
    # Get the next available ID by scanning existing todos
    try:
        existing_todos = list(todo.scan())
        if existing_todos:
            next_id = max([t.id for t in existing_todos]) + 1
        else:
            next_id = 1
    except:
        next_id = 1
    
    # Create and save the todo instance - THIS IS THE CORRECT WAY
    new_todo = todo(title=title, id=next_id, complete=False)
    new_todo.save()
    return redirect(url_for("home"))

@app.route("/update/<int:todo_id>")
def update(todo_id):
    # Since we need both hash_key (title) and range_key (id) to get an item,
    # we need to scan to find the item by ID
    try:
        for item in todo.scan():
            if item.id == todo_id:
                item.complete = not item.complete
                item.save()
                break
    except Exception as e:
        print(f"Error updating todo: {e}")
    
    return redirect(url_for("home"))

@app.route("/delete/<int:todo_id>")
def delete(todo_id):
    # Same approach - scan to find the item by ID
    try:
        for item in todo.scan():
            if item.id == todo_id:
                item.delete()
                break
    except Exception as e:
        print(f"Error deleting todo: {e}")
    
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=8080,debug=True)