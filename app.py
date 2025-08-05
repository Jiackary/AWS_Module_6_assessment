from flask import Flask, render_template_string, request, redirect, url_for
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, BooleanAttribute
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

app = Flask(__name__)


s3_client = boto3.client("s3", region_name="ap-southeast-1") 
bucket = "static-webpages-s3"

class todo(Model):
    class Meta:
        table_name = "todo"
        region_name = "ap-southeast-1"  
        
    
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
        
        search_query = request.args.get('search', '').strip()
        todo_list = list(todo.scan())
        

        if search_query:
            todo_list = [t for t in todo_list if search_query.lower() in t.title.lower()]
        
        response = s3_client.get_object(Bucket=bucket, Key="base.html")
        html_template = response['Body'].read().decode('utf-8')
        return render_template_string(html_template, todo_list=todo_list, search_query=search_query)
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500

@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title")
    # Get the next available ID by scanning existing todos
    try:
        if len(title)>=1:
            
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
        else:
             return redirect(url_for("home"))
    except:
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
    app.run(host="0.0.0.0", port=8080, debug=True)