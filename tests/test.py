import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
import io

from app import app # Import your Flask app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@patch('app.todo.scan')
@patch('app.todo.save')
def test_add_todo_item(mock_save, mock_scan, client):
  
    # Arrange: When the app checks for existing todos to find the next ID, return an empty list.
    mock_scan.return_value = []
    
    # Act: Post a new todo item
    response = client.post("/add", data={"title": "A new test todo"})

    # Assert: Check that the user is redirected (status 302)
    assert response.status_code == 302
    
    # Assert: Check that the save method on the todo model was called exactly once.
    mock_save.assert_called_once()


@patch('app.todo.scan')
def test_delete_todo_item(mock_scan, client):
    
    # Arrange: Create a mock object that will be "found" by the scan.
    # MagicMock can imitate any object and track calls to its methods.
    mock_item_to_delete = MagicMock()
    mock_item_to_delete.id = 123 # The ID we will try to delete
    mock_item_to_delete.title = "Delete Me"

    # Arrange: Make the scan return our mock item.
    mock_scan.return_value = [mock_item_to_delete]

    # Act: Call the delete route
    response = client.get("/delete/123")
    
    # Assert: Check that the user is redirected
    assert response.status_code == 302

    # Assert: Verify that the delete() method on our specific mock item was called.
    mock_item_to_delete.delete.assert_called_once()

@patch('app.todo.scan')
def test_update_changes_completion_status(mock_scan, client):
    
    # Arrange: Create a mock to-do item. MagicMock is perfect because it lets us
    # track changes to its attributes and calls to its methods (like .save()).
    mock_item = MagicMock()
    mock_item.id = 101
    mock_item.title = "A task to be completed"
    mock_item.complete = False  # Start with the item as incomplete

    # Arrange: Configure the mocked scan to return a list containing our mock item.
    mock_scan.return_value = [mock_item]

    # Act: Call the update endpoint for our specific item's ID.
    response = client.get("/update/101")

    # Assert: First, check that the page redirects as expected.
    assert response.status_code == 302

    # Assert: This is the key check! Verify the 'complete' status on our mock object
    # was flipped from False to True by the route's logic.
    assert mock_item.complete is True

    # Assert: We should also verify that the application attempted to save this change.
    mock_item.save.assert_called_once()