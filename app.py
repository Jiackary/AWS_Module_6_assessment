from flask import Flask, render_template_string, request, redirect, url_for, flash
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, NumberAttribute, BooleanAttribute, UTCDateTimeAttribute
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from datetime import datetime, timezone
import math

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'


s3_client = boto3.client("s3", region_name="ap-southeast-1") 
bucket = "static-webpages-s3"

class todo(Model):
    class Meta:
        table_name = "todo"
        region_name = "ap-southeast-1"  
        
    
    title = UnicodeAttribute(hash_key=True)
    id = NumberAttribute(range_key=True)
    complete = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute(default=lambda: datetime.now(timezone.utc))

@app.route("/")
def home():
    try:
        if not todo.exists():
            print("Table doesn't exist, creating...")
            todo.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)
            print("Table created successfully")
        

        search_query = request.args.get('search', '').strip()
        search_field = request.args.get('search_field', 'title')
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'asc')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 5))

        todo_list = list(todo.scan())

        if search_query:
            if search_field == 'title':
                todo_list = [t for t in todo_list if search_query.lower() in t.title.lower()]
            elif search_field == 'status':
                if search_query.lower() in ['complete', 'completed', 'done']:
                    todo_list = [t for t in todo_list if t.complete]
                elif search_query.lower() in ['incomplete', 'pending', 'todo']:
                    todo_list = [t for t in todo_list if not t.complete]
        
      
        if sort_by == 'title':
            todo_list.sort(key=lambda x: x.title.lower(), reverse=(sort_order == 'desc'))
        elif sort_by == 'created_at':
            todo_list.sort(key=lambda x: getattr(x, 'created_at', datetime.now(timezone.utc)), reverse=(sort_order == 'desc'))
        else: 
            todo_list.sort(key=lambda x: x.id, reverse=(sort_order == 'desc'))
        
   
        total_items = len(todo_list)
        total_pages = math.ceil(total_items / per_page)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_todos = todo_list[start_idx:end_idx]
        
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_page': page - 1 if page > 1 else None,
            'next_page': page + 1 if page < total_pages else None
        }
        
        response = s3_client.get_object(Bucket=bucket, Key="base.html")
        html_template = response['Body'].read().decode('utf-8')
        return render_template_string(html_template, 
                                    todo_list=paginated_todos, 
                                    search_query=search_query,
                                    search_field=search_field,
                                    sort_by=sort_by,
                                    sort_order=sort_order,
                                    pagination=pagination_info)
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500
    
@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title")
    
  
    if not title or not title.strip():
        return redirect(url_for("home"))
    
    title = title.strip()
    
    if len(title) < 1 or len(title) > 200:
        return redirect(url_for("home"))
    
    
    try:
        existing_todos = list(todo.scan())
        if existing_todos:
            next_id = max([t.id for t in existing_todos]) + 1
        else:
            next_id = 1
    except:
        next_id = 1
    
    try:
       
        new_todo = todo(title=title, id=next_id, complete=False, created_at=datetime.now(timezone.utc))
        new_todo.save()
        flash('Todo item created successfully!', 'success')
    except Exception as e:
        print(f"Error saving todo: {e}")
        flash('Error creating todo item', 'error')
    
    return redirect(url_for("home"))

@app.route("/update/<int:todo_id>")
def update(todo_id):

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

    try:
        deleted_title = None
        for item in todo.scan():
            if item.id == todo_id:
                deleted_title = item.title
                item.delete()
                break
        
        if deleted_title:
            flash(f'Todo item "{deleted_title}" has been permanently deleted.', 'success')
        else:
            flash('Todo item not found.', 'error')
    except Exception as e:
        print(f"Error deleting todo: {e}")
        flash('Error deleting todo item.', 'error')
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)